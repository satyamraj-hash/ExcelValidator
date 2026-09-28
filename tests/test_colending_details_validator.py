"""
Unit tests for ColendingDetailsValidator.
"""
import pytest
import pandas as pd
import src.modules.colending_details.validator
from src.modules.colending_details.validator import ColendingDetailsValidator
from src.core.models import Status

def test_basic_validation():
    v = ColendingDetailsValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "colending_partner": "TEST", "pl_principal_amount": "TEST", "sl_principal_amount": "TEST", "pl_interest_rate": "TEST", "sl_interest_rate": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = ColendingDetailsValidator()
    df = pd.DataFrame([{"loan_application_number": None, "colending_partner": None, "pl_principal_amount": None, "sl_principal_amount": None, "pl_interest_rate": None, "sl_interest_rate": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
