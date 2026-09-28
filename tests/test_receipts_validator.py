"""
Unit tests for ReceiptsValidator.
"""
import pytest
import pandas as pd
import src.modules.receipts.validator
from src.modules.receipts.validator import ReceiptsValidator
from src.core.models import Status

def test_basic_validation():
    v = ReceiptsValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "receipt_reference": "TEST", "receipt_amount": "TEST", "payment_mode": "TEST", "receipt_purpose": "TEST", "repayment_schedule_id": "TEST", "loan_charge_id": "TEST", "date_of_receipt": "TEST", "deposit_date": "TEST", "realization_date": "TEST", "instrument_number": "TEST", "transaction_date": "TEST", "receipt_status": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = ReceiptsValidator()
    df = pd.DataFrame([{"loan_application_number": None, "receipt_reference": None, "receipt_amount": None, "payment_mode": None, "receipt_purpose": None, "repayment_schedule_id": None, "loan_charge_id": None, "date_of_receipt": None, "deposit_date": None, "realization_date": None, "instrument_number": None, "transaction_date": None, "receipt_status": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
