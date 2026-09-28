"""
Unit tests for GstVerificationValidator.
"""
import pytest
import pandas as pd
import src.modules.gst_verification.validator
from src.modules.gst_verification.validator import GstVerificationValidator
from src.core.models import Status

def test_basic_validation():
    v = GstVerificationValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "cust_idx": "TEST", "gst_idx": "TEST", "gst_in": "TEST", "primary_business_address": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = GstVerificationValidator()
    df = pd.DataFrame([{"loan_application_number": None, "cust_idx": None, "gst_idx": None, "gst_in": None, "primary_business_address": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
