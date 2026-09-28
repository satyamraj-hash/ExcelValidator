"""
Unit tests for NachDetailValidator.
"""
import pytest
import pandas as pd
import src.modules.nach_detail.validator
from src.modules.nach_detail.validator import NachDetailValidator
from src.core.models import Status

def test_basic_validation():
    v = NachDetailValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "cust_idx": "TEST", "bank_idx": "TEST", "umrn": "TEST", "mandate_type": "TEST", "verification_status": "TEST", "is_active": "TEST", "mandate_amount_cap": "TEST", "frequency": "TEST", "mandate_start_date": "TEST", "mandate_expiry_date": "TEST", "contribution_type": "TEST", "repayment_holder_name": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = NachDetailValidator()
    df = pd.DataFrame([{"loan_application_number": None, "cust_idx": None, "bank_idx": None, "umrn": None, "mandate_type": None, "verification_status": None, "is_active": None, "mandate_amount_cap": None, "frequency": None, "mandate_start_date": None, "mandate_expiry_date": None, "contribution_type": None, "repayment_holder_name": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
