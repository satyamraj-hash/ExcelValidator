"""
Unit tests for CollateralValidator (COLL-001 through COLL-028).
"""

import sys
import os
import pytest
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.modules.collateral.validator import CollateralValidator
from src.core.models import Status, Severity


def make_df(rows):
    """Helper to create a DataFrame with standard collateral columns."""
    default = {
        "loan_id": None,
        "collateral_type": None,
        "collateral_subtype": None,
        "loan_account_number": None,
        "property_type": None,
        "nature_of_property": None,
        "is_building_constructed": None,
        "property_classification": None,
        "property_ownership": None,
        "market_value": None,
        "property_purpose": None,
        "residual_age_of_property": None,
        "address_json": None,
        "is_property_registered_in_favour_of_borrower": None,
        "is_security": None,
        "address_type": None,
        "country": None,
        "plot_number": None,
        "pincode": None,
        "region": None,
        "state": None,
        "city": None,
        "district": None,
        "taluka": None,
        "village": None,
        "seller_name": None,
        "present_registered_owner": None,
        "built_up_area": None,
        "carpet_area": None,
        "property_purpose.1": None,
    }
    records = []
    for r in rows:
        record = dict(default)
        record.update(r)
        records.append(record)
    return pd.DataFrame(records)


@pytest.fixture
def validator():
    return CollateralValidator()


class TestColl001LoanId:
    """COLL-001: loan_id mandatory, numeric integer, unique."""

    def test_valid_loan_id(self, validator):
        df = make_df([{"loan_id": 1001, "collateral_type": "building", "loan_account_number": "LN001"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-001" and r.status == Status.FAIL]
        assert len(fails) == 0

    def test_blank_loan_id(self, validator):
        df = make_df([{"loan_id": None, "collateral_type": "building", "loan_account_number": "LN001"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-001"]
        assert len(fails) > 0

    def test_non_numeric_loan_id(self, validator):
        df = make_df([{"loan_id": "ABCD", "collateral_type": "building", "loan_account_number": "LN001"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-001"]
        assert len(fails) > 0

    def test_decimal_loan_id(self, validator):
        df = make_df([{"loan_id": 1001.5, "collateral_type": "building", "loan_account_number": "LN001"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-001"]
        assert len(fails) > 0

    def test_duplicate_loan_id(self, validator):
        df = make_df([
            {"loan_id": 1001, "collateral_type": "building", "loan_account_number": "LN001"},
            {"loan_id": 1001, "collateral_type": "land", "loan_account_number": "LN002"},
        ])
        results = validator.validate(df)
        dup_fails = [r for r in results if r.rule_id == "COLL-001" and "Duplicate" in r.description]
        assert len(dup_fails) > 0


class TestColl002CollateralType:
    """COLL-002: collateral_type mandatory, valid configured value."""

    def test_valid_collateral_type(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-002"]
        assert len(fails) == 0

    def test_case_insensitive_collateral_type(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "Building", "loan_account_number": "LN001"}])
        results = validator.validate(df)
        # Building (mixed case) should still pass enum check (validator normalises to lowercase)
        enum_fails = [r for r in results if r.rule_id == "COLL-002" and "must be one of" in r.description]
        assert len(enum_fails) == 0

    def test_blank_collateral_type(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": None, "loan_account_number": "LN001"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-002"]
        assert len(fails) > 0

    def test_invalid_collateral_type(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "machinery", "loan_account_number": "LN001"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-002" and "must be one of" in r.description]
        assert len(fails) > 0


class TestColl003CollateralSubtype:
    """COLL-003: collateral_subtype optional, valid where populated."""

    def test_blank_subtype_passes(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "collateral_subtype": None}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-003"]
        assert len(fails) == 0

    def test_valid_subtype(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "collateral_subtype": "residential"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-003"]
        assert len(fails) == 0

    def test_invalid_subtype(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "collateral_subtype": "unknown_type"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-003"]
        assert len(fails) > 0


class TestColl004LoanAccountNumber:
    """COLL-004: loan_account_number mandatory, alphanumeric, unique."""

    def test_valid_loan_account_number(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN1234567890"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-004"]
        assert len(fails) == 0

    def test_blank_loan_account_number(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": None}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-004"]
        assert len(fails) > 0

    def test_duplicate_loan_account_number(self, validator):
        df = make_df([
            {"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001"},
            {"loan_id": 2, "collateral_type": "land", "loan_account_number": "LN001"},
        ])
        results = validator.validate(df)
        dup_fails = [r for r in results if r.rule_id == "COLL-004" and "Duplicate" in r.description]
        assert len(dup_fails) > 0


class TestColl005PropertyType:
    """COLL-005: property_type lowercase valid configured value where populated."""

    def test_residential_flat_valid_master_entry(self, validator):
        """DB master key 'residential_flat' MUST pass validation."""
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "property_type": "residential_flat"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-005"]
        assert len(fails) == 0

    def test_genuinely_invalid_property_type(self, validator):
        """Genuinely invalid value should fail validation."""
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "property_type": "invalid_property_kind_123"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-005"]
        assert len(fails) > 0


class TestColl006NatureOfProperty:
    """COLL-006: nature_of_property freehold/leasehold where populated."""

    def test_valid_freehold(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "nature_of_property": "freehold"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-006"]
        assert len(fails) == 0

    def test_invalid_nature(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "nature_of_property": "possession"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-006"]
        assert len(fails) > 0

    def test_blank_skipped(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "nature_of_property": None}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-006"]
        assert len(fails) == 0


class TestColl010MarketValue:
    """COLL-010: market_value numeric, > 0 where populated."""

    def test_valid_market_value(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "market_value": 5000000}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-010"]
        assert len(fails) == 0

    def test_zero_market_value(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "market_value": 0}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-010"]
        assert len(fails) > 0

    def test_negative_market_value(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "market_value": -100000}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-010"]
        assert len(fails) > 0

    def test_blank_market_value_skipped(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "market_value": None}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-010"]
        assert len(fails) == 0


class TestColl013AddressJson:
    """COLL-013: address_json valid JSON object where populated."""

    def test_valid_json(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001",
                        "address_json": '{"state": "Maharashtra", "pincode": "411046"}'}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-013"]
        assert len(fails) == 0

    def test_invalid_json(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001",
                        "address_json": "{invalid json}"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-013"]
        assert len(fails) > 0

    def test_blank_skipped(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001",
                        "address_json": None}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-013"]
        assert len(fails) == 0


class TestColl019Pincode:
    """COLL-019: pincode exactly 6 numeric digits where populated."""

    def test_valid_pincode(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "pincode": "411046"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-019"]
        assert len(fails) == 0

    def test_valid_pincode_as_float(self, validator):
        """Excel may read pincode as 411046.0 - validator should normalise."""
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "pincode": 411046.0}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-019"]
        assert len(fails) == 0

    def test_five_digit_pincode(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "pincode": "41104"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-019"]
        assert len(fails) > 0

    def test_alpha_pincode(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "pincode": "ABCDEF"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-019"]
        assert len(fails) > 0


class TestColl020Region:
    """COLL-020: region one of north/south/east/west."""

    def test_valid_region(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "region": "west"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-020"]
        assert len(fails) == 0

    def test_invalid_region(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001", "region": "central"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-020"]
        assert len(fails) > 0


class TestColl027CarpetArea:
    """COLL-027: carpet_area <= built_up_area."""

    def test_valid_carpet_vs_built_up(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001",
                        "built_up_area": 1200, "carpet_area": 1000}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-027" and "exceed" in r.description]
        assert len(fails) == 0

    def test_carpet_exceeds_built_up(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001",
                        "built_up_area": 800, "carpet_area": 1000}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-027" and "exceed" in r.description]
        assert len(fails) > 0


class TestColl028PropertyPurposeConsistency:
    """COLL-028: property_purpose and property_purpose.1 must match."""

    def test_matching_purposes(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001",
                        "property_purpose": "self-use", "property_purpose.1": "self-use"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-028"]
        assert len(fails) == 0

    def test_mismatched_purposes(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001",
                        "property_purpose": "rental", "property_purpose.1": "self-use"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-028"]
        assert len(fails) > 0

    def test_one_blank_skipped(self, validator):
        df = make_df([{"loan_id": 1, "collateral_type": "building", "loan_account_number": "LN001",
                        "property_purpose": None, "property_purpose.1": "rental"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "COLL-028"]
        assert len(fails) == 0


class TestActualExcelFile:
    """Integration test: Run validator against the actual collateral Excel file."""

    COLLATERAL_FILE = r"C:\Users\satyam.raj_synoriq\Downloads\Copy of 03_collateral_collateral_202312211146 (1).xlsx"

    def test_actual_collateral_file(self, validator):
        import os
        if not os.path.exists(self.COLLATERAL_FILE):
            pytest.skip("Actual collateral Excel file not found at expected path.")

        xl = pd.ExcelFile(self.COLLATERAL_FILE)
        sheet_name = xl.sheet_names[0]
        df = xl.parse(sheet_name)

        assert len(df) > 0, "Collateral Excel file has no data rows."

        results = validator.validate(df)
        errors = [r for r in results if r.severity == "ERROR" or r.severity.value == "ERROR"]
        print(f"\n[Actual file] Total rows: {len(df)}, Findings: {len(results)}, Errors: {len(errors)}")

        # Validator must not crash; findings should be a list
        assert isinstance(results, list)
