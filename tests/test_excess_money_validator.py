"""
Unit tests for ExcessMoneyValidator.
"""
import pytest
import pandas as pd
import src.modules.excess_money.validator
from src.modules.excess_money.validator import ExcessMoneyValidator
from src.core.models import Status

def test_basic_validation():
    v = ExcessMoneyValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "receipt_id": "TEST", "original_amount": "TEST", "excess_money": "TEST", "paid_amount": "TEST", "receipt_purpose": "TEST", "transaction_date": "TEST", "due_date": "TEST", "status": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = ExcessMoneyValidator()
    df = pd.DataFrame([{"loan_application_number": None, "receipt_id": None, "original_amount": None, "excess_money": None, "paid_amount": None, "receipt_purpose": None, "transaction_date": None, "due_date": None, "status": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
