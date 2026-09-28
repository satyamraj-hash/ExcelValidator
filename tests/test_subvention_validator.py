"""
Unit tests for SubventionValidator.
"""
import pytest
import pandas as pd
import src.modules.subvention.validator
from src.modules.subvention.validator import SubventionValidator
from src.core.models import Status

def test_basic_validation():
    v = SubventionValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "subvention_type": "TEST", "subvention_rate": "TEST", "subvention_amount": "TEST", "partner_id": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = SubventionValidator()
    df = pd.DataFrame([{"loan_application_number": None, "subvention_type": None, "subvention_rate": None, "subvention_amount": None, "partner_id": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
