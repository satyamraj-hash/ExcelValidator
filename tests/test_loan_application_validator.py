"""
Unit tests for LoanApplicationValidator (LA-001 through LA-060).
"""

from pathlib import Path
import pandas as pd
import pytest
from src.modules.loan_application.validator import LoanApplicationValidator
from src.core.models import Status, Severity


@pytest.fixture
def valid_loan_df() -> pd.DataFrame:
    """Fixture returning a valid Loan Application DataFrame passing all rules."""
    return pd.DataFrame({
        "loan_id": [601, 602],
        "loan_application_number": ["SHDG2028010", "SHDG2028011"],
        "source_application_number": ["SRC001", "SRC002"],
        "product_code": ["PL", "BL"],
        "branch_code": ["BR001", "BR002"],
        "interest_rate": [10.5, 12.0],
        "recovery_sub_type": ["revolving", "non_revolving"],
        "installment_frequency": ["monthly", "monthly"],
        "currency": [1, 1],
        "sanctioned_amount": [500000, 1000000],
        "disbursed_amount": [500000, 1000000],
        "requested_loan_amount": [500000, 1200000],
        "original_tenure": [36, 60],
        "current_tenure": [30, 60],
        "tenure_unit": ["months", "months"],
        "interest_start_date": ["2023-01-01", "2023-02-01"],
        "repayment_start_date": ["2023-02-01", "2023-03-01"],
        "sanction_date": ["2024-07-21", "2023-01-10"],
        "disbursal_date": ["2024-07-25", "2023-02-01"],
        "loan_booking_date": ["2024-07-22", "2023-01-05"],  # Booking after sanction date is explicitly allowed
        "disbursal_status": ["fully_disbursed", "fully_disbursed"],
        "loan_status": ["active", "closed"],
        "maturity_date": ["2026-01-01", "2028-02-01"],
        "installment_amount": [15000, 20000],
        "principal_outstanding": [400000, 0],
        "repayment_mode": ["nach", "ecs"],
        "irr": [12.5, 14.0],
        "emi_amount": [15000, 20000],
        "scheme_code": ["SC001", "SC002"],
        "is_colending": ["no", "yes"],
        "ltv_ratio": [80.0, 75.0],
        "foir": [40.0, 35.0],
        "paid_amount": [50000, 1000000],
        "loan_closure_date": [None, "2025-01-01"]
    })


def test_loan_application_validator_valid_data(valid_loan_df):
    validator = LoanApplicationValidator()
    results = validator.validate(valid_loan_df)
    failing_results = [r for r in results if r.status == Status.FAIL]
    assert len(failing_results) == 0


def test_loan_application_validator_dirty_rules():
    validator = LoanApplicationValidator()
    dirty_df = pd.DataFrame({
        "loan_id": ["NonInt", 601],                            # Duplicate 601 & NonInt
        "loan_application_number": ["INVALID!", "SHDG2028010"],
        "product_code": ["PL!", "BL"],
        "branch_code": ["BR001!", "BR002"],
        "interest_rate": [-5.0, 12.0],                         # Negative interest rate
        "recovery_sub_type": ["REVOLVING", "non_revolving"],   # Capitalized sub type
        "installment_frequency": ["Monthly", "monthly"],       # Capitalized frequency
        "sanctioned_amount": [500000, 1000000],
        "disbursed_amount": [600000, 1000000],                 # Disbursed > Sanctioned -> LA-012
        "requested_loan_amount": [-1000, 500000],
        "original_tenure": [36, 60],
        "current_tenure": [40, 60],                             # current > original -> LA-016
        "tenure_unit": ["Months", "months"],                    # Capitalized unit
        "interest_start_date": ["2023-05-01", "2023-01-01"],
        "repayment_start_date": ["2023-02-01", "2023-02-01"],   # interest > repayment -> LA-020
        "sanction_date": ["2023-02-01", "2023-01-10"],
        "disbursal_date": ["2023-01-01", "2023-02-01"],        # disbursal < sanction -> LA-023
        "loan_booking_date": ["2023-01-05", "2023-01-05"],
        "loan_status": ["CLOSED", "closed"],                    # Capitalized status & missing closure date -> LA-053
        "installment_amount": [15000, 20000],
        "principal_outstanding": [700000, 0],                   # outstanding > disbursed -> LA-032
        "repayment_mode": ["NACH", "nach"],                     # Capitalized repayment mode
        "irr": [12.5, 14.0],
        "emi_amount": [18000, 20000],                           # emi != installment -> LA-036
        "scheme_code": ["SC001", "SC002"],
        "ltv_ratio": [150.0, 75.0],                            # ltv > 100
        "foir": [40.0, 35.0],
        "paid_amount": [-500, 1000000]                          # Negative paid amount -> LA-058
    })

    results = validator.validate(dirty_df)
    rule_ids = {r.rule_id for r in results if r.status == Status.FAIL}

    assert "LA-001" in rule_ids
    assert "LA-006" in rule_ids
    assert "LA-007" in rule_ids
    assert "LA-008" in rule_ids
    assert "LA-012" in rule_ids
    assert "LA-016" in rule_ids
    assert "LA-017" in rule_ids
    assert "LA-020" in rule_ids
    assert "LA-023" in rule_ids
    assert "LA-027" in rule_ids
    assert "LA-032" in rule_ids
    assert "LA-033" in rule_ids
    assert "LA-036" in rule_ids
    assert "LA-041" in rule_ids
    assert "LA-053" in rule_ids
    assert "LA-058" in rule_ids


def test_loan_application_actual_excel_file():
    """Test validator directly against user's actual Loan Application Excel file."""
    user_file = Path(r"C:\Users\satyam.raj_synoriq\Downloads\Copy of 01_loan_application_loan_application_202312211108.xlsx")
    if not user_file.exists():
        pytest.skip("User Loan Application template file not found on system path.")

    df = pd.read_excel(user_file, sheet_name=0)
    validator = LoanApplicationValidator()
    results = validator.validate(df)

    missing_cols = [r for r in results if r.rule_id == "LOAN_STRUCT_001"]
    assert len(missing_cols) == 0, f"Missing columns in template: {[m.field for m in missing_cols]}"
