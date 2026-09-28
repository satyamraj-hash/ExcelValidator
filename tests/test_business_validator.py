"""
Unit tests for BusinessValidator.
"""
import pytest
import pandas as pd
import src.modules.business.validator
from src.modules.business.validator import BusinessValidator
from src.core.models import Status

def test_basic_validation():
    v = BusinessValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "cust_idx": "TEST", "company_or_firm_name": "TEST", "gross_monthly_income": "TEST", "nature_of_business": "TEST", "ownership": "TEST", "gst_number": "TEST", "constitution_type": "TEST", "full_address": "TEST", "pin_code": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = BusinessValidator()
    df = pd.DataFrame([{"loan_application_number": None, "cust_idx": None, "company_or_firm_name": None, "gross_monthly_income": None, "nature_of_business": None, "ownership": None, "gst_number": None, "constitution_type": None, "full_address": None, "pin_code": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
