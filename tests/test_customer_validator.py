"""
Unit tests for CustomerValidator business rules (TC01 to TC27).
"""

from pathlib import Path
import pandas as pd
import pytest
from src.modules.customer.validator import CustomerValidator
from src.core.models import Status, Severity


@pytest.fixture
def valid_customer_df() -> pd.DataFrame:
    """Fixture returning a 100% clean Customer DataFrame passing all rules."""
    return pd.DataFrame({
        "loan_application_number": ["SHDG2028010", "SHDG2028010", "SHDG2028011"],
        "customer_id": [123456, 123457, 123458],
        "customer_relationship_id": ["CUST026572", "CUST026573", "CUST026574"],
        "customer_type": ["applicant", "co-applicant", "applicant"],
        "first_name": ["John", "Jane", "Alice"],
        "last_name": ["Doe", "Smith", "Johnson"],
        "dob": ["1990-01-01", "1992-05-15", "1988-11-20"],
        "category": ["Salaried", "Self-employed", "general"],
        "marital_status": ["married", "single", "married"],
        "pan": ["BAQPK0750C", "BAQPK0751D", "BAQPK0752E"],
        "aadhar_number": ["123456789012", "xxxxxxxx0008", "987654321098"],
        "phone1": ["8699786256", "8699273635", "9027362361"],
        "gender": ["male", "female", "female"],
        "religion": ["hindu", "muslim", "christian"],
        "current_address": ["Omkara tower", "123 Main St", "456 Park Ave"],
        "current_city": ["Jaipur", "Mumbai", "Delhi"],
        "current_landmark": ["Vaishali nagar", "Near Mall", "Opposite Metro"],
        "current_district": ["Jaipur", "Mumbai", "Delhi"],
        "current_address_type": ["Residential", "Residential", "Office"],
        "permanent_address": ["Omkara tower", "123 Main St", "456 Park Ave"],
        "permanent_city": ["Jaipur", "Mumbai", "Delhi"],
        "permanent_ladmark": ["Vaishali nagar", "Near Mall", "Opposite Metro"],
        "permanent_district": ["Jaipur", "Mumbai", "Delhi"],
        "permanent_address_type": ["Residential", "Residential", "Office"],
        "cibil": [750, 800, 650],
        "is_individual": ["true", "true", "true"],
        "pincode": ["302020", "400001", "110001"]
    })


def test_customer_validator_valid_data(valid_customer_df):
    validator = CustomerValidator()
    results = validator.validate(valid_customer_df)
    failing_results = [r for r in results if r.status == Status.FAIL]
    assert len(failing_results) == 0


def test_customer_validator_missing_columns():
    validator = CustomerValidator()
    incomplete_df = pd.DataFrame({
        "first_name": ["John"],
        "last_name": ["Doe"]
    })
    results = validator.validate(incomplete_df)
    missing_col_results = [r for r in results if "MISSING" in str(r.actual_value)]
    assert len(missing_col_results) == len(validator.required_columns) - 2


def test_customer_validator_dirty_rules():
    validator = CustomerValidator()
    dirty_df = pd.DataFrame({
        "loan_application_number": ["INVALID!APP#", "SHDG2028010"],
        "customer_id": ["NonInteger", 123457],
        "customer_type": ["INVALID_TYPE", "co-applicant"],
        "first_name": ["John123", "Jane"],
        "last_name": ["Doe", "Smith"],
        "dob": ["2099-01-01", "invalid-date"],
        "category": ["INVALID_CAT", "Salaried"],
        "marital_status": ["INVALID_MARITAL", "single"],
        "pan": ["INVALID_PAN", "BAQPK0750C"],
        "aadhar_number": ["123", "xxxxxxxx0008"],
        "phone1": ["12345", "8699786256"],
        "gender": ["INVALID_GENDER", "female"],
        "religion": ["INVALID_RELIGION", "hindu"],
        "current_address": ["Addr", "Addr"],
        "current_city": ["City", "City"],
        "current_landmark": ["Landmark", "Landmark"],
        "current_district": ["District", "District"],
        "current_address_type": ["Type", "Type"],
        "permanent_address": ["Addr", "Addr"],
        "permanent_city": ["City", "City"],
        "permanent_ladmark": ["Landmark", "Landmark"],
        "permanent_district": ["District", "District"],
        "permanent_address_type": ["Type", "Type"],
        "cibil": [150, 1000],
    })
    
    results = validator.validate(dirty_df)
    rule_ids = {r.rule_id for r in results if r.status == Status.FAIL}

    assert "CUST_TC03" in rule_ids
    assert "CUST_TC04" in rule_ids
    assert "CUST_TC05" in rule_ids
    assert "CUST_TC06" in rule_ids
    assert "CUST_TC07" in rule_ids
    assert "CUST_TC08" in rule_ids
    assert "CUST_TC09" in rule_ids
    assert "CUST_TC10" in rule_ids
    assert "CUST_TC11" in rule_ids
    assert "CUST_TC12" in rule_ids
    assert "CUST_TC17" in rule_ids
    assert "CUST_TC22" in rule_ids
    assert "CUST_TC24" in rule_ids


def test_customer_validator_actual_excel_file():
    """Test validator directly against user's actual Excel template file."""
    user_file = Path(r"C:\Users\satyam.raj_synoriq\Downloads\Copy of 02_customer_customer_202312211120 (1).xlsx")
    if not user_file.exists():
        pytest.skip("User template file not found on system path.")

    df = pd.read_excel(user_file, sheet_name=0)
    validator = CustomerValidator()
    results = validator.validate(df)

    # Ensure structural checks pass on actual file
    missing_cols = [r for r in results if r.rule_id == "CUST_STRUCT_001"]
    assert len(missing_cols) == 0, f"Missing columns in template: {[m.field for m in missing_cols]}"
