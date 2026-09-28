"""
Unit tests for ChargesValidator.
"""
import pytest
import pandas as pd
import src.modules.charges.validator
from src.modules.charges.validator import ChargesValidator
from src.core.models import Status

def test_basic_validation():
    v = ChargesValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "loan_charge_id": "TEST", "charge_code": "TEST", "original_amount": "TEST", "paid_amount": "TEST", "pending_amount": "TEST", "waived_amount": "TEST", "tax_amount": "TEST", "is_tax_applicable": "TEST", "payment_status": "TEST", "receivable_payable": "TEST", "charge_stage": "TEST", "due_date": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = ChargesValidator()
    df = pd.DataFrame([{"loan_application_number": None, "loan_charge_id": None, "charge_code": None, "original_amount": None, "paid_amount": None, "pending_amount": None, "waived_amount": None, "tax_amount": None, "is_tax_applicable": None, "payment_status": None, "receivable_payable": None, "charge_stage": None, "due_date": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
