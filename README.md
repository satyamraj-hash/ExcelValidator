# Excel Migration Validator 📊

A professional, scalable Python & Streamlit enterprise web application for validating Excel data prior to system migration.

Designed with a modular, extensible architecture supporting **20+ Excel migration modules** (e.g., Customer, Loan Application, Repayment Schedule, Receipts, Loan Charges, Collateral, NACH, SPDC, Disbursal Schedule, Disbursal Breakup).

---

## 🎯 Project Purpose

During core banking and financial system migrations, legacy data stored in Excel workbooks often contains missing mandatory fields, invalid data formats, illegal domain/master lookup codes, duplicate key records, out-of-range financial amounts, or illegal dates.

The **Excel Migration Validator** automates pre-migration data quality assurance by:
1. Parsing uploaded Excel files (`.xlsx`, `.xls`).
2. Applying unique, rule-based validations per module (supporting **ERROR** and **WARNING** severities).
3. Displaying interactive executive summaries and filterable data finding tables in Streamlit.
4. Generating downloadable multi-tab Excel validation reports (Summary Dashboard + Detailed Findings) using OpenPyXL.

---

## 🏗️ Project Architecture

The codebase strictly decouples UI presentation from validation and business domain logic:

```
excel-validator/
├── .gitignore               # Excludes bytecode, virtualenv, client data files
├── README.md                # Project documentation and setup guide
├── requirements.txt         # Dependencies (Streamlit, Pandas, OpenPyXL, Pytest)
├── app/                     # Presentation Layer (Streamlit UI)
│   ├── __init__.py
│   └── main.py              # Main Web App UI Shell & Dashboard
├── src/                     # Core Business & Validation Engine
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py        # ValidationResult, Severity, Status, ValidationSummary models
│   │   ├── base.py          # BaseValidator abstract class & ValidationRule schema
│   │   ├── registry.py      # ValidatorRegistry dynamic module loader
│   │   ├── utils.py         # Reusable pure validation helper functions
│   │   └── report_generator.py # OpenPyXL styled multi-tab report generator
│   └── modules/             # Module-Specific Validators
│       ├── __init__.py
│       └── customer/
│           ├── __init__.py
│           └── validator.py # CustomerValidator Skeleton Interface
└── tests/                   # Pytest Automated Test Suite
    ├── __init__.py
    ├── conftest.py          # Shared test fixtures
    ├── test_core_models.py
    ├── test_core_utils.py
    ├── test_registry.py
    ├── test_report_generator.py
    └── test_customer_validator.py
```

### Standardized Validation Result Schema

Every validation rule evaluation generates a `ValidationResult` object with:
- **`Rule ID`**: Unique identifier (e.g., `CUST_REQ_001`, `CUST_PAN_002`)
- **`Module`**: Target module name (e.g., `Customer`)
- **`Field/Column`**: Column header evaluated
- **`Severity`**: `ERROR` or `WARNING`
- **`Status`**: `PASS` or `FAIL`
- **`Description`**: Contextual rule violation message
- **`Row Number`**: 1-indexed Excel row number (Row 1 = Header)
- **`Actual Value`**: Cell value found in Excel
- **`Expected Value`**: Required format/bound/type description

---

## 🚀 How to Install Dependencies

1. Clone or navigate to the repository directory:
   ```bash
   cd C:\Users\satyam.raj_synoriq\Desktop\excel-validator
   ```

2. Activate your Python virtual environment (if using `.venv`):
   ```powershell
   .venv\Scripts\activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🌐 GitHub + Streamlit Deployment

This project is ready to be deployed on Streamlit Cloud from a public GitHub repository.

### Recommended deployment flow

1. Push the repository to GitHub.
2. Open Streamlit Cloud and create a new app.
3. Connect the GitHub repository.
4. In the app settings, select the file path:
   ```bash
   streamlit_app.py
   ```
5. Keep the Python version set to 3.10 or newer.
6. Deploy the app.

### Local equivalent

```bash
streamlit run streamlit_app.py
```

This project already includes the required dependency file at `requirements.txt` and a Streamlit-compatible entrypoint at `streamlit_app.py`.

---

## 💻 How to Run the Streamlit Application

Run the Streamlit application using:

```bash
streamlit run streamlit_app.py
```

The application will launch in your browser at `http://localhost:8501`.

---

## 🧪 How to Run Tests

Execute the automated test suite with Pytest:

```bash
pytest -v
```

---

## 🧩 How to Add New Migration Modules (e.g., Loan Application, Repayment Schedule)

Adding a new module does **NOT** require modifying core engine files or UI code:

1. Create a new directory under `src/modules/` (e.g., `src/modules/loan_application/`).
2. Implement a new class inheriting from `BaseValidator`:

   ```python
   from typing import List
   import pandas as pd
   from src.core.base import BaseValidator, ValidationRule
   from src.core.models import ValidationResult
   from src.core.registry import registry
   from src.core.utils import validate_missing_values

   class LoanApplicationValidator(BaseValidator):
       @property
       def module_name(self) -> str:
           return "Loan Application"

       @property
       def required_columns(self) -> List[str]:
           return ["Loan_ID", "Customer_ID", "Loan_Amount", "Disbursal_Date"]

       def get_rules_metadata(self) -> List[ValidationRule]:
           return [...]

       def _run_validations(self, df: pd.DataFrame) -> List[ValidationResult]:
           results = []
           # Add module validations using reusable helper utilities from src.core.utils
           return results

   # Auto-register with the registry
   registry.register(LoanApplicationValidator)
   ```

3. Import the new validator package in `app/main.py`. The module will automatically appear in the Streamlit dropdown list!
