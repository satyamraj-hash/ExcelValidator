"""
Unit tests for ClassificationHistoryValidator.
"""
import pytest
import pandas as pd
import src.modules.classification_history.validator
from src.modules.classification_history.validator import ClassificationHistoryValidator
from src.core.models import Status

def test_basic_validation():
    v = ClassificationHistoryValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "transaction_date": "TEST", "value_date": "TEST", "current_asset_classification": "TEST", "next_asset_classification": "TEST", "accounting_classification": "TEST", "days_past_due": "TEST", "transaction_narration": "TEST", "manual_movement_flag": "TEST", "previous_classification_date": "TEST", "asset_classification_date": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = ClassificationHistoryValidator()
    df = pd.DataFrame([{"loan_application_number": None, "transaction_date": None, "value_date": None, "current_asset_classification": None, "next_asset_classification": None, "accounting_classification": None, "days_past_due": None, "transaction_narration": None, "manual_movement_flag": None, "previous_classification_date": None, "asset_classification_date": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
