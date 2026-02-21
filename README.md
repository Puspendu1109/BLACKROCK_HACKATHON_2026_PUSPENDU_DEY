# BlackRock Challenge Solution - PUSPENDU-DEY

This repository contains the business logic and REST API for the BlackRock Challenge. The solution is built using **Python 3.11** and **FastAPI**, engineered for high performance and low memory consumption. 

The application has been fully containerized using Docker, strictly adhering to the hackathon's infrastructure requirements.


## 📂 Project Structure

```text
.
├── app.py                 # Main FastAPI application and core business logic
├── Dockerfile             # Container definition (Exposes port 5477)
├── compose.yaml           # Docker Compose configuration for API and testing
├── requirements.txt       # Python dependencies
└── test/
    └── test_app.py        # Bonus: Unit and integration tests (pytest)
```
## Deatiled explanation of app.py

**1. Imports & Initializations:**

*   `from fastapi import FastAPI`: Imports the FastAPI library, which is used for creating web APIs.
*   `from pydantic import BaseModel, Field`: Imports `BaseModel` and `Field` from Pydantic, a library for data validation and serialization. It's used for defining the structure of request and response data.
*   `from typing import List, Optional, Tuple`: Imports type hints for improved code readability and maintainability.
*   `from datetime import datetime`: Imports the `datetime` class for working with dates and times.
*   `from decimal import Decimal, ROUND_HALF_UP`: Imports `Decimal` for performing calculations with decimal numbers (important for precision) and `ROUND_HALF_UP` for rounding to the nearest decimal place.
*   `from functools import lru_cache`: Imports `lru_cache` for caching function results, improving performance.
*   `import threading`: Imports the threading module for multi-threading.
*   `import os`: Imports the `os` module for interacting with the operating system (e.g., reading files).
*   `import bisect`: Imports the `bisect` module for binary search. It's used for efficient searching within sorted lists.
*   `import logging`: Imports the logging module for debugging and monitoring.

**2. FastAPI Setup:**

*   `app = FastAPI()`: Creates an instance of the FastAPI application.

**3. MODELS:**

*   `class TransactionInput(BaseModel):`: Defines a `TransactionInput` class, which serves as the model for the incoming transaction data.  It conforms to `BaseModel` and utilizes `Field` for data validation.
*   `class EnrichedTransaction(BaseModel):`: Defines a `EnrichedTransaction` class, representing a transaction with more detailed data. It utilizes `Field` to define the attributes of the transaction.
*   `class TransactionOutput(BaseModel):`: Defines a `TransactionOutput` class that specifies the structure of the transaction data that the API returns.
*   `class PeriodQ(BaseModel):`: Defines a `PeriodQ` class to represent a period (e.g., a day, week, month).
*   `class PeriodP(BaseModel):`: Defines a `PeriodP` class representing a period (e.g. week).
*   `class PeriodK(BaseModel):`: Defines a `PeriodK` class representing a period (e.g. month).
*   `class ValidTransaction(BaseModel):`: Defines a class to represent a valid transaction, containing important elements like correct data types and validated information.

**4. API Endpoints:**

*   `@app.get("/blackrock/challenge/v1/performance")`: Defines a REST API endpoint `/blackrock/challenge/v1/performance` that retrieves performance information.
*   `async def performance_report():`:  A function that returns a JSON response containing the performance data.
*   `@app.post("/blackrock/challenge/v1/transactions:parse", response_model=List[EnrichedTransaction])`: Defines a POST endpoint `/blackrock/challenge/v1/transactions:parse` that parses the transaction data.  It returns a list of `EnrichedTransaction` objects.
*   `@app.post("/blackrock/challenge/v1/transactions:validator", response_model=ValidatorResponse)`: Defines a POST endpoint `/blackrock/challenge/v1/transactions:validator` that validates the transaction data.
*   `@app.post("/blackrock/challenge/v1/transactions:filter", response_model=ValidatorResponse)`: Defines a POST endpoint `/blackrock/challenge/v1/transactions:filter` that filters the transaction data based on specified criteria.
*   `@app.post("/blackrock/challenge/v1/returns:nps", response_model=ReturnsResponse)`: Defines a POST endpoint `/blackrock/challenge/v1/returns:nps` that calculates and returns the return value for each transaction.
*   `@app.post("/blackrock/challenge/v1/returns:index", response_model=ReturnsResponse)`: Defines a POST endpoint `/blackrock/challenge/v1/returns:index` that returns the index of a transaction.

**5. Data Validation & Processing:**

*   `result = []`: Initializes an empty list to store the processed transaction data.
*   The code iterates through the transactions and, for each transaction:
    *   It calculates the remanent value.
    *   It appends the `EnrichedTransaction` object to the `result` list.

**6. API Responses:**

*   The responses provided for each endpoint return JSON data, formatted as a dictionary, which contains the calculated values.
*   The `return` statements in the endpoints return valid transaction objects.

**7.  Logging:**

*   `logging.info(...)`: Logs informational messages to the console.

**8.  Error Handling:**

*   The code includes basic error handling within the `validate_transactions` and `returns_nps` functions.

## 🚀 Prerequisites

* **Docker** installed and running on host machine.
* **Docker Compose** (V2 recommended, using the `docker compose` command).

---

## 🛠️ Build and Run Instructions

### Option 1: Using Standard Docker Commands (As Requested)

**1. Build the image:**
Run the following command in the root directory to build the Linux-based image:

```bash
docker build -t blk-hacking-ind-PUSPENDU-DEY .

```

**2. Run the container:**
Map the required port (`5477`) and start the application in detached mode:

```bash
docker run -d -p 5477:5477 blk-hacking-ind-PUSPENDU-DEY

```

### Option 2: Using Docker Compose

For convenience, a `compose.yaml` file is included.

**Start the API:**

```bash
docker compose up api -d

```

The application will be accessible at `http://localhost:5477`.

---

## 🧪 Running the Tests (Bonus Evaluation)

Comprehensive unit and integration tests have been provided in the `test/test_app.py` file to validate mathematical precision (taxes, compound interest, remanent calculations) and endpoint logic.

To execute the validations securely within the containerized environment using Docker Compose:

```bash
docker compose up test

```

*Note: This command runs `pytest test/test_app.py -v` internally, executing the validations exactly as specified in the test file's metadata comment.*

---

## 📖 API Documentation

Once the container is running, FastAPI automatically generates interactive API documentation which can be found from here. 

* **Swagger UI:** [http://localhost:5477/docs](https://www.google.com/search?q=http://localhost:5477/docs)
* **ReDoc:** [http://localhost:5477/redoc](https://www.google.com/search?q=http://localhost:5477/redoc)

### Available Endpoints

* `GET /blackrock/challenge/v1/performance` - Retrieves application memory usage and execution time.
* `POST /blackrock/challenge/v1/transactions:parse` - Calculates transaction ceiling and remanent.
* `POST /blackrock/challenge/v1/transactions:validator` - Filters out duplicate and negative transactions.
* `POST /blackrock/challenge/v1/transactions:filter` - Applies temporal rules (Q, P, K periods) to transactions.
* `POST /blackrock/challenge/v1/returns:nps` - Calculates NPS returns (including tax benefits).
* `POST /blackrock/challenge/v1/returns:index` - Calculates Index returns.

