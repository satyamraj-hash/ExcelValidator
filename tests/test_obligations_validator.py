"""
Unit tests for ObligationsValidator.
"""
import pytest
import pandas as pd
import src.modules.obligations.validator
from src.modules.obligations.validator import ObligationsValidator
from src.core.models import Status

def test_basic_validation():
    v = ObligationsValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "cust_idx": "TEST", "obl_idx": "TEST", "financial_institution": "TEST", "loan_amount": "TEST", "emi_amount": "TEST", "remaining_loan_balance": "TEST", "obligation_type": "TEST", "installment_frequency": "TEST", "is_bt": "TEST", "remarks": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = ObligationsValidator()
    df = pd.DataFrame([{"loan_application_number": None, "cust_idx": None, "obl_idx": None, "financial_institution": None, "loan_amount": None, "emi_amount": None, "remaining_loan_balance": None, "obligation_type": None, "installment_frequency": None, "is_bt": None, "remarks": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
