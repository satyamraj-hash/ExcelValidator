"""
Unit tests for PaymentsValidator.
"""
import pytest
import pandas as pd
import src.modules.payments.validator
from src.modules.payments.validator import PaymentsValidator
from src.core.models import Status

def test_basic_validation():
    v = PaymentsValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "payment_id": "TEST", "payment_date": "TEST", "original_amount": "TEST", "paid_amount": "TEST", "payment_mode": "TEST", "payment_status": "TEST", "payment_reference_number": "TEST", "payment_method": "TEST", "paid_to": "TEST", "beneficiary_account_number": "TEST", "ifsc_code": "TEST", "beneficiary_account_type": "TEST", "utr": "TEST", "instrument_number": "TEST", "instrument_date": "TEST", "disbursal_breakup_id": "TEST", "refund_against": "TEST", "is_auto_payment": "TEST", "transaction_date": "TEST", "remarks": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = PaymentsValidator()
    df = pd.DataFrame([{"loan_application_number": None, "payment_id": None, "payment_date": None, "original_amount": None, "paid_amount": None, "payment_mode": None, "payment_status": None, "payment_reference_number": None, "payment_method": None, "paid_to": None, "beneficiary_account_number": None, "ifsc_code": None, "beneficiary_account_type": None, "utr": None, "instrument_number": None, "instrument_date": None, "disbursal_breakup_id": None, "refund_against": None, "is_auto_payment": None, "transaction_date": None, "remarks": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
