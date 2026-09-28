"""
Unit tests for InstitutionValidator.
"""
import pytest
import pandas as pd
import src.modules.institution.validator
from src.modules.institution.validator import InstitutionValidator
from src.core.models import Status

def test_basic_validation():
    v = InstitutionValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "cust_idx": "TEST", "employer_name": "TEST", "industry": "TEST", "designation": "TEST", "commencment_date": "TEST", "remarks": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = InstitutionValidator()
    df = pd.DataFrame([{"loan_application_number": None, "cust_idx": None, "employer_name": None, "industry": None, "designation": None, "commencment_date": None, "remarks": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
