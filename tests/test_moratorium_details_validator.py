"""
Unit tests for MoratoriumDetailsValidator.
"""
import pytest
import pandas as pd
import src.modules.moratorium_details.validator
from src.modules.moratorium_details.validator import MoratoriumDetailsValidator
from src.core.models import Status

def test_basic_validation():
    v = MoratoriumDetailsValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "moratorium_treatment_type": "TEST", "number_of_moratorium_installments": "TEST", "fixed_installment_amount": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = MoratoriumDetailsValidator()
    df = pd.DataFrame([{"loan_application_number": None, "moratorium_treatment_type": None, "number_of_moratorium_installments": None, "fixed_installment_amount": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
