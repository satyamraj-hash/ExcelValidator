"""
Pytest shared fixtures.
"""

import pytest
import pandas as pd


@pytest.fixture
def sample_customer_df() -> pd.DataFrame:
    """Fixture providing a mock DataFrame for testing."""
    return pd.DataFrame({
        "Customer_ID": ["CUST001", "CUST002", "CUST003", "CUST001"],  # duplicate CUST001
        "Full_Name": ["John Doe", "Jane Smith", "", None],             # missing values
        "Age": [25, 150, "InvalidAge", 30],                             # numeric range / invalid
        "PAN": ["ABCDE1234F", "12345", "XYZ123", "ABCDE5678G"],         # regex test
        "Gender": ["MALE", "FEMALE", "OTHER", "UNKNOWN"],              # allowed values test
        "DOB": ["1990-01-15", "15/01/1990", "2020-13-45", "1995-05-20"] # date format test
    })


@pytest.fixture
def clean_df() -> pd.DataFrame:
    """Fixture providing clean valid data."""
    return pd.DataFrame({
        "Customer_ID": ["CUST001", "CUST002"],
        "Full_Name": ["John Doe", "Jane Smith"],
        "Age": [25, 30],
        "PAN": ["ABCDE1234F", "XYZAB5678G"],
        "Gender": ["MALE", "FEMALE"],
        "DOB": ["1990-01-15", "1995-05-20"]
    })
