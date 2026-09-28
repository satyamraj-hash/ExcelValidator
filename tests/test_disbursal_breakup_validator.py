"""
Unit tests for DisbursalBreakupValidator.
"""
import pytest
import pandas as pd
import src.modules.disbursal_breakup.validator
from src.modules.disbursal_breakup.validator import DisbursalBreakupValidator
from src.core.models import Status

def test_basic_validation():
    v = DisbursalBreakupValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "disbursal_number": "TEST", "breakup_number": "TEST", "payment_date": "TEST", "gross_disbursed_amount": "TEST", "adjusted_charges": "TEST", "disbursal_amount": "TEST", "paid_amount": "TEST", "payment_status": "TEST", "bank_name": "TEST", "ifsc_code": "TEST", "account_number": "TEST", "account_type": "TEST", "bank_branch": "TEST", "payment_mode": "TEST", "utr": "TEST", "instrument_number": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = DisbursalBreakupValidator()
    df = pd.DataFrame([{"loan_application_number": None, "disbursal_number": None, "breakup_number": None, "payment_date": None, "gross_disbursed_amount": None, "adjusted_charges": None, "disbursal_amount": None, "paid_amount": None, "payment_status": None, "bank_name": None, "ifsc_code": None, "account_number": None, "account_type": None, "bank_branch": None, "payment_mode": None, "utr": None, "instrument_number": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
