from fastapi import FastAPI
from pydantic import BaseModel,Field
from typing import List, Optional, Tuple
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
import threading
import os
import bisect
import logging


app = FastAPI()

# ==========================================
# --- MODELS ---
# ==========================================
class TransactionInput(BaseModel):
    date: str 
    amount: Decimal = Field(..., ge=0)

class EnrichedTransaction(BaseModel):
    date: str
    amount: Decimal
    ceiling: Decimal
    remanent: Decimal

class TransactionOutput(BaseModel):
    date: str
    amount: Decimal
    ceiling: Decimal
    remanent: Decimal
    inkPeriod: Optional[bool] = None
    message: Optional[str] = None

class PeriodQ(BaseModel):
    fixed: Decimal
    start: str
    end: str

class PeriodP(BaseModel):
    extra: Decimal
    start: str
    end: str

class PeriodK(BaseModel):
    start: str
    end: str

class ValidatorRequest(BaseModel):
    wage: Decimal
    transactions: List[TransactionOutput]

class ValidatorResponse(BaseModel):
    valid: List[TransactionOutput]
    invalid: List[TransactionOutput]

class FilterRequest(BaseModel):
    q: List[PeriodQ] = []
    p: List[PeriodP] = []
    k: List[PeriodK] = []
    wage: Decimal
    transactions: List[TransactionOutput]

class ReturnsRequest(BaseModel):
    age: int = Field(..., ge=18, le=100) # Assuming realistic age boundaries
    wage: Decimal = Field(..., ge=0)
    inflation: Decimal = Field(..., ge=0)
    q: List[PeriodQ] = []
    p: List[PeriodP] = []
    k: List[PeriodK] = []
    transactions: List[TransactionOutput]

class SavingsByDate(BaseModel):
    start: str
    end: str
    amount: Decimal
    profit: Optional[Decimal] = None
    taxBenefit: Optional[Decimal] = None

class ReturnsResponse(BaseModel):
    totalTransactionAmount: Decimal
    totalCeiling: Decimal
    savingsByDates: List[SavingsByDate]


# ==========================================
# --- OPTIMIZED UTILITY FUNCTIONS ---
# ==========================================

def get_memory_usage_mb() -> float:
    """Reads RSS memory usage from Linux /proc filesystem (Docker friendly, no psutil)"""
    try:
        with open('/proc/self/status') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    # VmRSS:     10240 kB -> convert to MB
                    return float(line.split()[1]) / 1024.0
    except FileNotFoundError:
        return 0.0
    return 0.0



THRESHOLDS = [
    Decimal('700000'), 
    Decimal('1000000'), 
    Decimal('1200000'), 
    Decimal('1500000')
]

PREV_THRESHOLDS = [
    Decimal('0'), 
    Decimal('700000'), 
    Decimal('1000000'), 
    Decimal('1200000'), 
    Decimal('1500000')
]

BASE_TAX = [
    Decimal('0'),       
    Decimal('0'),       
    Decimal('30000'),   
    Decimal('60000'),   
    Decimal('120000')   
]

RATES = [
    Decimal('0.0'), 
    Decimal('0.10'), 
    Decimal('0.15'), 
    Decimal('0.20'), 
    Decimal('0.30')
]

@lru_cache(maxsize=10000)
def parse_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        logging.error(f"Failed to parse date string '{date_str}': {e}")
        raise ValueError(f"Date parsing error: {e}")

@lru_cache(maxsize=1024)
def calculate_tax(yearly_income: Decimal) -> Decimal:
    try:
        # 1. Find the correct bracket index using binary search
        idx = bisect.bisect_right(THRESHOLDS, yearly_income)
        
        # 2. Calculate tax: Base Tax + (Excess Income * Marginal Rate)
        tax = BASE_TAX[idx] + (yearly_income - PREV_THRESHOLDS[idx]) * RATES[idx]
        
        return tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except Exception as e:
        logging.error(f"Failed to calculate tax for income {yearly_income}: {e}")
        raise RuntimeError(f"Tax calculation error: {e}")

def calculate_remanent(amount: Decimal) -> Decimal:
    try:
        hundred = Decimal('100')
        remanent = (hundred - amount % hundred) % hundred
        return remanent.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except Exception as e:
        logging.error(f"Failed to calculate remanent for amount {amount}: {e}")
        raise RuntimeError(f"Remanent calculation error: {e}")

def fast_compound_math(period_amount: float, rate: float, inflation_rate: float, years: int) -> Tuple[float, float]:
    """Standard Python math is fast enough here without Numba compilation overhead."""
    try:
        future_value = period_amount * ((1.0 + rate) ** years)
        real_value = future_value / ((1.0 + (inflation_rate / 100.0)) ** years)
        return future_value, real_value
    except Exception as e:
        logging.error(f"Failed fast compound math (Amount: {period_amount}, Rate: {rate}): {e}")
        raise RuntimeError(f"Compound math error: {e}")

def process_transaction_rules_fast(
    tx_date: datetime, 
    current_remanent: Decimal, 
    parsed_q: List[Tuple[datetime, datetime, Decimal, int]], 
    parsed_p: List[Tuple[datetime, datetime, Decimal]]
) -> Decimal:
    try:
        applicable_qs = [
            (q_start, q_idx, q_fixed) 
            for q_start, q_end, q_fixed, q_idx in parsed_q 
            if q_start <= tx_date <= q_end
        ]
        
        if applicable_qs:
            applicable_qs.sort(key=lambda x: (x[0], x[1]), reverse=True)
            current_remanent = applicable_qs[0][2]

        for p_start, p_end, p_extra in parsed_p:
            if p_start <= tx_date <= p_end:
                current_remanent += p_extra
                
        return current_remanent
    except Exception as e:
        logging.error(f"Failed to process transaction rules for date {tx_date}: {e}")
        raise RuntimeError(f"Transaction rules error: {e}")

def calculate_returns(payload: 'ReturnsRequest', rate: float, is_nps: bool) -> 'ReturnsResponse':
    try:
        parsed_q = [(parse_date(q.start), parse_date(q.end), q.fixed, idx) for idx, q in enumerate(payload.q)]
        parsed_p = [(parse_date(p.start), parse_date(p.end), p.extra) for p in payload.p]
        parsed_k = [(parse_date(k.start), parse_date(k.end), k.start, k.end) for k in payload.k]

        valid_txs = []
        seen_dates = set()
        total_tx_amount = Decimal('0.0')
        total_ceiling = Decimal('0.0')
        
        for tx in payload.transactions:
            if tx.amount >= 0 and tx.date not in seen_dates:
                seen_dates.add(tx.date)
                tx_dt = parse_date(tx.date)
                tx.remanent = process_transaction_rules_fast(tx_dt, tx.remanent, parsed_q, parsed_p)
                valid_txs.append((tx_dt, tx.remanent))
                total_tx_amount += tx.amount
                total_ceiling += tx.ceiling

        savings_by_dates = []
        yearly_income = payload.wage * Decimal('12')
        years_to_invest = max(60 - payload.age, 5)
        inf_rate_float = float(payload.inflation)
        
        for k_start_dt, k_end_dt, k_start_str, k_end_str in parsed_k:
            period_amount = sum(
                (rem for dt, rem in valid_txs if k_start_dt <= dt <= k_end_dt), 
                Decimal('0.0')
            )
            
            _, real_value = fast_compound_math(float(period_amount), rate, inf_rate_float, years_to_invest)
            
            profit = (Decimal(str(real_value)) - period_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            tax_benefit = Decimal('0.0')
            if is_nps:
                deduction = min(period_amount, Decimal('0.10') * yearly_income, Decimal('200000.0'))
                base_tax = calculate_tax(yearly_income)
                new_tax = calculate_tax(yearly_income - deduction)
                tax_benefit = (base_tax - new_tax).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
            savings_by_dates.append(SavingsByDate(
                start=k_start_str,
                end=k_end_str,
                amount=period_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                profit=profit,
                taxBenefit=tax_benefit if is_nps else None
            ))

        return ReturnsResponse(
            totalTransactionAmount=total_tx_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            totalCeiling=total_ceiling.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            savingsByDates=savings_by_dates
        )
    except Exception as e:
        logging.error(f"Failed to calculate returns: {e}")
        raise RuntimeError(f"Calculate returns processing error: {e}")
# ==========================================
# --- ENDPOINTS ---
# ==========================================

@app.get("/blackrock/challenge/v1/performance")
async def performance_report():
    memory_mb = get_memory_usage_mb()
    return {
        "time": datetime.utcnow().strftime("%H:%M:%S.%f")[:-3],
        "memory": f"{memory_mb:.2f} MB",
        "threads": threading.active_count()
        # "cache_info": {
        #     "date_parser": parse_date.cache_info()._asdict()
        # }
    }

@app.post("/blackrock/challenge/v1/transactions:parse", response_model=List[EnrichedTransaction])
async def parse_transactions(transactions: List[TransactionInput]):
    result = []
    for tx in transactions:
        remanent = calculate_remanent(tx.amount)
        result.append(EnrichedTransaction(
            date=tx.date, amount=tx.amount, ceiling=tx.amount + remanent, remanent=remanent
        ))
    return result

@app.post("/blackrock/challenge/v1/transactions:validator", response_model=ValidatorResponse)
async def validate_transactions(payload: ValidatorRequest):
    valid, invalid = [], []
    seen_dates = set()

    for tx in payload.transactions:
        if tx.amount < 0:
            tx.message = "Negative amounts are not allowed"
            invalid.append(tx)
        elif tx.date in seen_dates:
            tx.message = "Duplicate transaction"
            invalid.append(tx)
        else:
            seen_dates.add(tx.date)
            valid.append(tx)

    return ValidatorResponse(valid=valid, invalid=invalid)

@app.post("/blackrock/challenge/v1/transactions:filter", response_model=ValidatorResponse)
async def filter_transactions(payload: FilterRequest):
    valid, invalid = [], []
    seen_dates = set()

    parsed_q = [(parse_date(q.start), parse_date(q.end), q.fixed, idx) for idx, q in enumerate(payload.q)]
    parsed_p = [(parse_date(p.start), parse_date(p.end), p.extra) for p in payload.p]
    parsed_k = [(parse_date(k.start), parse_date(k.end)) for k in payload.k]

    for tx in payload.transactions:
        if tx.amount < 0:
            tx.message = "Negative amounts are not allowed"
            invalid.append(tx)
            continue
        if tx.date in seen_dates:
            tx.message = "Duplicate transaction"
            invalid.append(tx)
            continue
            
        seen_dates.add(tx.date)
        tx_dt = parse_date(tx.date)
        
        tx.remanent = process_transaction_rules_fast(tx_dt, tx.remanent, parsed_q, parsed_p)
        tx.inkPeriod = any(k_start <= tx_dt <= k_end for k_start, k_end in parsed_k)
            
        valid.append(tx)

    return ValidatorResponse(valid=valid, invalid=invalid)

@app.post("/blackrock/challenge/v1/returns:nps", response_model=ReturnsResponse)
async def returns_nps(payload: ReturnsRequest):
    return calculate_returns(payload, rate=0.0711, is_nps=True)

@app.post("/blackrock/challenge/v1/returns:index", response_model=ReturnsResponse)
async def returns_index(payload: ReturnsRequest):
    return calculate_returns(payload, rate=0.1449, is_nps=False)