"""
Unit tests for CustomerInsuranceValidator.
"""
import pytest
import pandas as pd
import src.modules.customer_insurance.validator
from src.modules.customer_insurance.validator import CustomerInsuranceValidator
from src.core.models import Status

def test_basic_validation():
    v = CustomerInsuranceValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "cust_idx": "TEST", "ins_idx": "TEST", "insurance_type": "TEST", "insurance_vendor": "TEST", "policy_no": "TEST", "insurance_premium": "TEST", "insurance_amount": "TEST", "policy_start_date": "TEST", "policy_end_date": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = CustomerInsuranceValidator()
    df = pd.DataFrame([{"loan_application_number": None, "cust_idx": None, "ins_idx": None, "insurance_type": None, "insurance_vendor": None, "policy_no": None, "insurance_premium": None, "insurance_amount": None, "policy_start_date": None, "policy_end_date": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
