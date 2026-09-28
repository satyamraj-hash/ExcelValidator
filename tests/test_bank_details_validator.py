"""
Unit tests for BankDetailsValidator — BANK-001 through BANK-016.
"""

import pytest
import pandas as pd

import src.modules.bank_details.validator  # noqa: F401 — triggers registry
from src.modules.bank_details.validator import BankDetailsValidator
from src.core.models import Severity, Status


# ---------------------------------------------------------------------------
# Helper factory
# ---------------------------------------------------------------------------

def make_df(**overrides):
    """Return a single-row DataFrame with all required fields valid by default."""
    base = {
        "loan_application_number": "LN-001",
        "cust_idx": 1,
        "bank_idx": 1,
        "account_number": 1083000100116600,
        "branch_ifsc": "SBIN0004306",
        "account_holder_name": "Ramesh Kumar",
        "bank_name": "State Bank of India",
        "account_type": "savings",
        "micr_code": None,
        "is_repayment_account": True,
        "is_disbursal_account": True,
        "is_default_account": True,
        "bank_address": None,
    }
    base.update(overrides)
    return pd.DataFrame([base])


def get_errors(df, rule_id=None):
    """Run validator and return FAIL results, optionally filtered by rule_id."""
    v = BankDetailsValidator()
    results = v.validate(df)
    fails = [r for r in results if r.status == Status.FAIL]
    if rule_id:
        fails = [r for r in fails if r.rule_id == rule_id]
    return fails


# ---------------------------------------------------------------------------
# BANK-001: loan_application_number mandatory
# ---------------------------------------------------------------------------

class TestBank001:
    def test_blank_loan_id_errors(self):
        df = make_df(loan_application_number=None)
        assert get_errors(df, "BANK-001"), "Expected BANK-001 error for blank loan_application_number"

    def test_present_loan_id_passes(self):
        df = make_df(loan_application_number="LN-001")
        assert not get_errors(df, "BANK-001")


# ---------------------------------------------------------------------------
# BANK-002: cust_idx mandatory + numeric
# ---------------------------------------------------------------------------

class TestBank002:
    def test_blank_cust_idx_errors(self):
        df = make_df(cust_idx=None)
        assert get_errors(df, "BANK-002")

    def test_non_numeric_cust_idx_errors(self):
        df = make_df(cust_idx="ABC")
        assert get_errors(df, "BANK-002")

    def test_valid_cust_idx_passes(self):
        df = make_df(cust_idx=1)
        assert not get_errors(df, "BANK-002")

    def test_numeric_string_cust_idx_passes(self):
        df = make_df(cust_idx="2")
        assert not get_errors(df, "BANK-002")


# ---------------------------------------------------------------------------
# BANK-003: bank_idx mandatory + numeric
# ---------------------------------------------------------------------------

class TestBank003:
    def test_blank_bank_idx_errors(self):
        df = make_df(bank_idx=None)
        assert get_errors(df, "BANK-003")

    def test_non_numeric_bank_idx_errors(self):
        df = make_df(bank_idx="X")
        assert get_errors(df, "BANK-003")

    def test_valid_bank_idx_passes(self):
        df = make_df(bank_idx=1)
        assert not get_errors(df, "BANK-003")


# ---------------------------------------------------------------------------
# BANK-004: account_number mandatory
# ---------------------------------------------------------------------------

class TestBank004:
    def test_blank_account_number_errors(self):
        df = make_df(account_number=None)
        assert get_errors(df, "BANK-004")

    def test_present_account_number_passes(self):
        df = make_df(account_number=1083000100116600)
        assert not get_errors(df, "BANK-004")


# ---------------------------------------------------------------------------
# BANK-005: account_number numeric
# ---------------------------------------------------------------------------

class TestBank005:
    def test_non_numeric_account_number_errors(self):
        df = make_df(account_number="ACCT-XYZ")
        assert get_errors(df, "BANK-005")

    def test_numeric_account_number_passes(self):
        df = make_df(account_number=1234567890)
        assert not get_errors(df, "BANK-005")

    def test_numeric_string_account_number_passes(self):
        df = make_df(account_number="1234567890")
        assert not get_errors(df, "BANK-005")


# ---------------------------------------------------------------------------
# BANK-006: branch_ifsc mandatory
# ---------------------------------------------------------------------------

class TestBank006:
    def test_blank_ifsc_errors(self):
        df = make_df(branch_ifsc=None)
        assert get_errors(df, "BANK-006")

    def test_present_ifsc_passes(self):
        df = make_df(branch_ifsc="SBIN0004306")
        assert not get_errors(df, "BANK-006")


# ---------------------------------------------------------------------------
# BANK-007: branch_ifsc format
# ---------------------------------------------------------------------------

class TestBank007:
    def test_valid_ifsc_passes(self):
        for ifsc in ["SBIN0004306", "HDFC0001234", "ICIC0000001", "UTIB0000AAA"]:
            df = make_df(branch_ifsc=ifsc)
            assert not get_errors(df, "BANK-007"), f"Expected {ifsc} to pass BANK-007"

    def test_invalid_ifsc_too_short(self):
        df = make_df(branch_ifsc="SBI004306")
        assert get_errors(df, "BANK-007")

    def test_invalid_ifsc_wrong_fifth_char(self):
        df = make_df(branch_ifsc="SBIN1004306")  # 5th char is '1' not '0'
        assert get_errors(df, "BANK-007")

    def test_invalid_ifsc_starts_with_number(self):
        df = make_df(branch_ifsc="1BIN0004306")
        assert get_errors(df, "BANK-007")

    def test_invalid_ifsc_too_long(self):
        df = make_df(branch_ifsc="SBIN00043067")
        assert get_errors(df, "BANK-007")


# ---------------------------------------------------------------------------
# BANK-008: account_holder_name mandatory
# ---------------------------------------------------------------------------

class TestBank008:
    def test_blank_name_errors(self):
        df = make_df(account_holder_name=None)
        assert get_errors(df, "BANK-008")

    def test_present_name_passes(self):
        df = make_df(account_holder_name="Ramesh Kumar")
        assert not get_errors(df, "BANK-008")


# ---------------------------------------------------------------------------
# BANK-009: bank_name mandatory
# ---------------------------------------------------------------------------

class TestBank009:
    def test_blank_bank_name_errors(self):
        df = make_df(bank_name=None)
        assert get_errors(df, "BANK-009")

    def test_present_bank_name_passes(self):
        df = make_df(bank_name="State Bank of India")
        assert not get_errors(df, "BANK-009")


# ---------------------------------------------------------------------------
# BANK-010: account_type enum
# ---------------------------------------------------------------------------

class TestBank010:
    def test_valid_account_types_pass(self):
        for atype in ["savings", "current", "cash_credit", "overdraft"]:
            df = make_df(account_type=atype)
            assert not get_errors(df, "BANK-010"), f"Expected {atype} to pass BANK-010"

    def test_invalid_account_type_errors(self):
        df = make_df(account_type="salary")
        assert get_errors(df, "BANK-010")

    def test_blank_account_type_errors(self):
        df = make_df(account_type=None)
        assert get_errors(df, "BANK-010")


# ---------------------------------------------------------------------------
# BANK-011: is_repayment_account boolean
# ---------------------------------------------------------------------------

class TestBank011:
    def test_bool_true_passes(self):
        df = make_df(is_repayment_account=True)
        assert not get_errors(df, "BANK-011")

    def test_bool_false_passes(self):
        df = make_df(is_repayment_account=False)
        assert not get_errors(df, "BANK-011")

    def test_string_true_passes(self):
        df = make_df(is_repayment_account="True")
        assert not get_errors(df, "BANK-011")

    def test_invalid_value_errors(self):
        df = make_df(is_repayment_account="maybe")
        assert get_errors(df, "BANK-011")


# ---------------------------------------------------------------------------
# BANK-012: is_disbursal_account boolean
# ---------------------------------------------------------------------------

class TestBank012:
    def test_bool_passes(self):
        df = make_df(is_disbursal_account=True)
        assert not get_errors(df, "BANK-012")

    def test_invalid_errors(self):
        df = make_df(is_disbursal_account="yes_please")
        assert get_errors(df, "BANK-012")


# ---------------------------------------------------------------------------
# BANK-013: is_default_account boolean
# ---------------------------------------------------------------------------

class TestBank013:
    def test_bool_passes(self):
        df = make_df(is_default_account=False)
        assert not get_errors(df, "BANK-013")

    def test_invalid_errors(self):
        df = make_df(is_default_account="default")
        assert get_errors(df, "BANK-013")


# ---------------------------------------------------------------------------
# BANK-014: duplicate composite key
# ---------------------------------------------------------------------------

class TestBank014:
    def test_duplicate_composite_key_errors(self):
        row1 = {
            "loan_application_number": "LN-001", "cust_idx": 1, "bank_idx": 1,
            "account_number": 111, "branch_ifsc": "SBIN0004306",
            "account_holder_name": "A", "bank_name": "SBI",
            "account_type": "savings", "micr_code": None,
            "is_repayment_account": True, "is_disbursal_account": True,
            "is_default_account": True, "bank_address": None,
        }
        row2 = dict(row1)  # identical composite key
        df = pd.DataFrame([row1, row2])
        assert get_errors(df, "BANK-014"), "Duplicate composite key should produce BANK-014 error"

    def test_unique_composite_key_passes(self):
        row1 = {
            "loan_application_number": "LN-001", "cust_idx": 1, "bank_idx": 1,
            "account_number": 111, "branch_ifsc": "SBIN0004306",
            "account_holder_name": "A", "bank_name": "SBI",
            "account_type": "savings", "micr_code": None,
            "is_repayment_account": True, "is_disbursal_account": True,
            "is_default_account": True, "bank_address": None,
        }
        row2 = dict(row1)
        row2["bank_idx"] = 2  # different bank_idx → different key
        df = pd.DataFrame([row1, row2])
        assert not get_errors(df, "BANK-014")


# ---------------------------------------------------------------------------
# BANK-015: micr_code optional — numeric when present
# ---------------------------------------------------------------------------

class TestBank015:
    def test_blank_micr_passes(self):
        df = make_df(micr_code=None)
        assert not get_errors(df, "BANK-015")

    def test_numeric_micr_passes(self):
        df = make_df(micr_code=400002009)
        assert not get_errors(df, "BANK-015")

    def test_non_numeric_micr_errors(self):
        df = make_df(micr_code="ABCXYZ")
        assert get_errors(df, "BANK-015")


# ---------------------------------------------------------------------------
# BANK-016: bank_address optional — not blank when provided
# ---------------------------------------------------------------------------

class TestBank016:
    def test_blank_address_field_passes(self):
        df = make_df(bank_address=None)
        assert not get_errors(df, "BANK-016")

    def test_valid_address_passes(self):
        df = make_df(bank_address="12, MG Road, Jaipur")
        assert not get_errors(df, "BANK-016")

    def test_whitespace_only_address_errors(self):
        df = make_df(bank_address="   ")
        assert get_errors(df, "BANK-016")
