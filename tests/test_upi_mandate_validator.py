"""
Unit tests for UpiMandateValidator.
"""
import pytest
import pandas as pd
import src.modules.upi_mandate.validator
from src.modules.upi_mandate.validator import UpiMandateValidator
from src.core.models import Status

def test_basic_validation():
    v = UpiMandateValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "cust_idx": "TEST", "customer_vpa": "TEST", "maximum_installment_amount": "TEST", "mandate_reference_number": "TEST", "customer_mobile_number": "TEST", "mandate_effective_date": "TEST", "mandate_expiry_date": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = UpiMandateValidator()
    df = pd.DataFrame([{"loan_application_number": None, "cust_idx": None, "customer_vpa": None, "maximum_installment_amount": None, "mandate_reference_number": None, "customer_mobile_number": None, "mandate_effective_date": None, "mandate_expiry_date": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
