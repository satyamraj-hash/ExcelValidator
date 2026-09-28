"""
Unit tests for SpdcValidator.
"""
import pytest
import pandas as pd
import src.modules.spdc.validator
from src.modules.spdc.validator import SpdcValidator
from src.core.models import Status

def test_basic_validation():
    v = SpdcValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "spdc_idx": "TEST", "bank_account_number": "TEST", "cheque_number": "TEST", "cheque_amount": "TEST", "instrument_type": "TEST", "instrument_status": "TEST", "is_security": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = SpdcValidator()
    df = pd.DataFrame([{"loan_application_number": None, "spdc_idx": None, "bank_account_number": None, "cheque_number": None, "cheque_amount": None, "instrument_type": None, "instrument_status": None, "is_security": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
