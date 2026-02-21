# 1. Test type: Unit and Integration Testing
# 2. Validation to be executed: Validates core utility math functions (tax, remanent, compound interest) and all REST API endpoints (parsing, validation, filtering, and returns).
# 3. Command with the necessary arguments for execution: pytest test/test_app.py -v

import pytest
from fastapi.testclient import TestClient
from decimal import Decimal
import sys
import os

# Ensure the root directory is in the path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, calculate_tax, calculate_remanent, fast_compound_math

client = TestClient(app)

# ==========================================
# --- UNIT TESTS ---
# ==========================================

def test_calculate_remanent():
    # Amount is 10.50 -> Next multiple of 100 is 100. Remanent = 89.50
    assert calculate_remanent(Decimal('10.50')) == Decimal('89.50')
    # Amount is 100.00 -> Remanent = 0.00
    assert calculate_remanent(Decimal('100.00')) == Decimal('0.00')
    # Amount is 150.00 -> Next multiple of 100 is 200. Remanent = 50.00
    assert calculate_remanent(Decimal('150.00')) == Decimal('50.00')

def test_calculate_tax():
    # Income below 700,000 -> 0 tax
    assert calculate_tax(Decimal('500000')) == Decimal('0.00')
    # Income in the 10% bracket (700,000 - 1,000,000)
    assert calculate_tax(Decimal('800000')) == Decimal('10000.00')

def test_fast_compound_math():
    future, real = fast_compound_math(1000.0, 0.10, 5.0, 10)
    # 1000 * (1.10)^10 = 2593.74
    assert round(future, 2) == 2593.74
    # Real value adjusted for 5% inflation over 10 years
    assert round(real, 2) == 1592.33

# ==========================================
# --- INTEGRATION TESTS (ENDPOINTS) ---
# ==========================================

def test_performance_report():
    response = client.get("/blackrock/challenge/v1/performance")
    assert response.status_code == 200
    data = response.json()
    assert "time" in data
    assert "memory" in data
    assert "threads" in data

def test_parse_transactions():
    payload = [
        {"date": "2023-01-01 10:00:00", "amount": 25.50},
        {"date": "2023-01-02 10:00:00", "amount": 100.00}
    ]
    response = client.post("/blackrock/challenge/v1/transactions:parse", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 2
    assert data[0]["remanent"] == 74.50
    assert data[0]["ceiling"] == 100.00
    assert data[1]["remanent"] == 0.00

def test_validate_transactions():
    payload = {
        "wage": 50000.0,
        "transactions": [
            {"date": "2023-01-01 10:00:00", "amount": 50.0, "ceiling": 100.0, "remanent": 50.0},
            {"date": "2023-01-01 10:00:00", "amount": 20.0, "ceiling": 100.0, "remanent": 80.0}, # Duplicate date
            {"date": "2023-01-02 10:00:00", "amount": -10.0, "ceiling": 0.0, "remanent": 0.0}   # Negative
        ]
    }
    response = client.post("/blackrock/challenge/v1/transactions:validator", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["valid"]) == 1
    assert len(data["invalid"]) == 2
    assert data["invalid"][0]["message"] == "Duplicate transaction"
    assert data["invalid"][1]["message"] == "Negative amounts are not allowed"

def test_filter_transactions():
    payload = {
        "q": [{"fixed": 100.0, "start": "2023-01-01 00:00:00", "end": "2023-01-31 23:59:59"}],
        "p": [{"extra": 20.0, "start": "2023-01-01 00:00:00", "end": "2023-01-31 23:59:59"}],
        "k": [{"start": "2023-01-15 00:00:00", "end": "2023-01-20 23:59:59"}],
        "wage": 50000.0,
        "transactions": [
            {"date": "2023-01-16 10:00:00", "amount": 50.0, "ceiling": 100.0, "remanent": 50.0}
        ]
    }
    response = client.post("/blackrock/challenge/v1/transactions:filter", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    tx = data["valid"][0]
    # Remanent should be Fixed (100) + Extra (20) = 120
    assert tx["remanent"] == 120.0
    # Date is inside period K, so inkPeriod should be true
    assert tx["inkPeriod"] is True

def test_returns_nps():
    payload = {
        "age": 30,
        "wage": 100000.0, # Yearly income: 1.2M
        "inflation": 5.0,
        "k": [{"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}],
        "transactions": [
            {"date": "2023-06-01 10:00:00", "amount": 50.0, "ceiling": 100.0, "remanent": 50.0}
        ]
    }
    response = client.post("/blackrock/challenge/v1/returns:nps", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["totalTransactionAmount"] == 50.0
    assert len(data["savingsByDates"]) == 1
    
    saving = data["savingsByDates"][0]
    assert saving["amount"] == 50.0
    assert "profit" in saving
    # Tax benefit must be present for NPS
    assert "taxBenefit" in saving 
    assert saving["taxBenefit"] is not None

def test_returns_index():
    payload = {
        "age": 30,
        "wage": 100000.0,
        "inflation": 5.0,
        "k": [{"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}],
        "transactions": [
            {"date": "2023-06-01 10:00:00", "amount": 50.0, "ceiling": 100.0, "remanent": 50.0}
        ]
    }
    response = client.post("/blackrock/challenge/v1/returns:index", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    saving = data["savingsByDates"][0]
    # Tax benefit must be None for Index
    assert saving["taxBenefit"] is None