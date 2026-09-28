"""
Unit tests for IncomeInformationValidator.
"""
import pytest
import pandas as pd
import src.modules.income_information.validator
from src.modules.income_information.validator import IncomeInformationValidator
from src.core.models import Status

def test_basic_validation():
    v = IncomeInformationValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "cust_idx": "TEST", "income_idx": "TEST", "source": "TEST", "income": "TEST", "income_frequency": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = IncomeInformationValidator()
    df = pd.DataFrame([{"loan_application_number": None, "cust_idx": None, "income_idx": None, "source": None, "income": None, "income_frequency": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
