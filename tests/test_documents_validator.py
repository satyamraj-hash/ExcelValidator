"""
Unit tests for DocumentsValidator.
"""
import pytest
import pandas as pd
import src.modules.documents.validator
from src.modules.documents.validator import DocumentsValidator
from src.core.models import Status

def test_basic_validation():
    v = DocumentsValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "parent_type": "TEST", "doc_idx": "TEST", "document_type": "TEST", "document_url": "TEST", "description": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = DocumentsValidator()
    df = pd.DataFrame([{"loan_application_number": None, "parent_type": None, "doc_idx": None, "document_type": None, "document_url": None, "description": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
