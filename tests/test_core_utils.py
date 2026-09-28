"""
Unit tests for reusable validation utility functions.
"""

import pandas as pd
from src.core.utils import (
    is_blank,
    validate_missing_values,
    validate_regex_pattern,
    validate_allowed_values,
    validate_numeric_range,
    validate_duplicates,
    validate_date_format,
)


def test_is_blank():
    assert is_blank(None) is True
    assert is_blank("") is True
    assert is_blank("   ") is True
    assert is_blank(float("nan")) is True
    assert is_blank("John") is False
    assert is_blank(123) is False


def test_validate_missing_values(sample_customer_df):
    findings = validate_missing_values(
        df=sample_customer_df,
        column="Full_Name",
        rule_id="R_REQ_01",
        module="Customer"
    )
    # Row 3 ("") and Row 4 (None) should fail -> Excel row numbers 4 and 5
    assert len(findings) == 2
    assert findings[0]["row_number"] == 4
    assert findings[1]["row_number"] == 5


def test_validate_regex_pattern(sample_customer_df):
    pan_pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
    findings = validate_regex_pattern(
        df=sample_customer_df,
        column="PAN",
        pattern=pan_pattern,
        rule_id="R_PAN_01",
        module="Customer"
    )
    # Row 2 ("12345") and Row 3 ("XYZ123") should fail regex
    assert len(findings) == 2
    assert findings[0]["actual_value"] == "12345"
    assert findings[1]["actual_value"] == "XYZ123"


def test_validate_allowed_values(sample_customer_df):
    findings = validate_allowed_values(
        df=sample_customer_df,
        column="Gender",
        allowed_values=["MALE", "FEMALE", "OTHER"],
        rule_id="R_GEN_01",
        module="Customer"
    )
    # Row 4 ("UNKNOWN") is invalid
    assert len(findings) == 1
    assert findings[0]["actual_value"] == "UNKNOWN"


def test_validate_numeric_range(sample_customer_df):
    findings = validate_numeric_range(
        df=sample_customer_df,
        column="Age",
        min_val=18,
        max_val=100,
        rule_id="R_AGE_01",
        module="Customer"
    )
    # Row 2 (150 > 100) and Row 3 ("InvalidAge" non-numeric) fail
    assert len(findings) == 2


def test_validate_duplicates(sample_customer_df):
    findings = validate_duplicates(
        df=sample_customer_df,
        columns=["Customer_ID"],
        rule_id="R_DUP_01",
        module="Customer"
    )
    # CUST001 is duplicated on row 2 and row 5
    assert len(findings) == 2


def test_validate_date_format(sample_customer_df):
    findings = validate_date_format(
        df=sample_customer_df,
        column="DOB",
        date_format="%Y-%m-%d",
        rule_id="R_DOB_01",
        module="Customer"
    )
    # "15/01/1990" and "2020-13-45" fail YYYY-MM-DD format
    assert len(findings) == 2
