"""
Unit tests for RepaymentScheduleValidator (RPS-001 through RPS-074).
"""

import sys
import os
import pytest
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.modules.repayment_schedule.validator import RepaymentScheduleValidator
from src.core.models import Status, Severity


def make_df(rows):
    """Helper to create a DataFrame with standard repayment schedule columns."""
    default = {
        "loan_id": "L1001",
        "loan_application_number": None,
        "loan_account_no": None,
        "due_date": "2024-01-01",
        "opening_balance": 100000.0,
        "installment_amount": 10000.0,
        "status": "pending",
        "principal": 8000.0,
        "interest": 2000.0,
        "closing_balance": 92000.0,
        "installment_number": 1,
        "received_amount": 0.0,
        "pending_amount": 10000.0,
        "is_advance_repayment": "no",
        "advance_prepay_flag": None,
        "billed_flag": "false",
        "billed_date": None,
        "tds_rate": 0,
        "tds_amount": 0,
        "installment_indicator": None,
    }
    records = []
    for r in rows:
        record = dict(default)
        record.update(r)
        records.append(record)
    return pd.DataFrame(records)


@pytest.fixture
def validator():
    return RepaymentScheduleValidator()


class TestCategory1Identification:
    """RPS-001 - RPS-005: Loan Identification & Advance Flag."""

    def test_both_loan_identifiers_blank(self, validator):
        df = make_df([{"loan_id": None, "loan_application_number": None, "loan_account_no": None}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-001"]
        assert len(fails) > 0

    def test_app_number_provided(self, validator):
        df = make_df([{"loan_application_number": "APP123"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-001"]
        assert len(fails) == 0

    def test_advance_repayment_missing_flag(self, validator):
        df = make_df([{"loan_id": "L1", "is_advance_repayment": "yes", "advance_prepay_flag": None}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-004"]
        assert len(fails) > 0

    def test_advance_repayment_valid_flag(self, validator):
        df = make_df([{"loan_id": "L1", "is_advance_repayment": "yes", "advance_prepay_flag": "ADV_1"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-004"]
        assert len(fails) == 0


class TestCategory2Calculations:
    """RPS-006 - RPS-009: Calculations."""

    def test_installment_amount_mismatch(self, validator):
        df = make_df([{"loan_id": "L1", "installment_amount": 15000.0, "principal": 8000.0, "interest": 2000.0}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-007"]
        assert len(fails) > 0

    def test_closing_balance_mismatch(self, validator):
        df = make_df([{"loan_id": "L1", "opening_balance": 100000.0, "principal": 8000.0, "closing_balance": 50000.0}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-009"]
        assert len(fails) > 0


class TestCategory3NegativeAmounts:
    """RPS-010 - RPS-016: Negative Amounts."""

    def test_negative_principal(self, validator):
        df = make_df([{"loan_id": "L1", "principal": -500.0}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-010"]
        assert len(fails) > 0

    def test_negative_interest(self, validator):
        df = make_df([{"loan_id": "L1", "interest": -100.0}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-011"]
        assert len(fails) > 0


class TestCategory4StatusVsAmount:
    """RPS-017 - RPS-026: Status vs Amounts."""

    def test_paid_status_received_mismatch(self, validator):
        df = make_df([{"loan_id": "L1", "status": "paid", "installment_amount": 10000.0, "received_amount": 5000.0, "pending_amount": 0.0}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-018"]
        assert len(fails) > 0

    def test_paid_status_pending_positive(self, validator):
        df = make_df([{"loan_id": "L1", "status": "paid", "installment_amount": 10000.0, "received_amount": 10000.0, "pending_amount": 500.0}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-020"]
        assert len(fails) > 0

    def test_pending_status_received_positive(self, validator):
        df = make_df([{"loan_id": "L1", "status": "pending", "received_amount": 1000.0}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-022"]
        assert len(fails) > 0


class TestCategory5InstallmentSequence:
    """RPS-027 - RPS-033: Installment Sequence."""

    def test_invalid_sequence_start(self, validator):
        df = make_df([{"loan_id": "L1", "installment_number": 5}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-029"]
        assert len(fails) > 0

    def test_missing_installment_gap(self, validator):
        df = make_df([
            {"loan_id": "L1", "installment_number": 1},
            {"loan_id": "L1", "installment_number": 2},
            {"loan_id": "L1", "installment_number": 5},
        ])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-030"]
        assert len(fails) > 0

    def test_duplicate_installment(self, validator):
        df = make_df([
            {"loan_id": "L1", "installment_number": 1},
            {"loan_id": "L1", "installment_number": 1},
        ])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-032"]
        assert len(fails) > 0


class TestCategory6DueDate:
    """RPS-034 - RPS-037: Due Date."""

    def test_duplicate_due_date(self, validator):
        df = make_df([
            {"loan_id": "L1", "installment_number": 1, "due_date": "2024-01-01"},
            {"loan_id": "L1", "installment_number": 2, "due_date": "2024-01-01"},
        ])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-034"]
        assert len(fails) > 0

    def test_chronology_warning(self, validator):
        df = make_df([
            {"loan_id": "L1", "installment_number": 1, "due_date": "2024-02-01"},
            {"loan_id": "L1", "installment_number": 2, "due_date": "2024-01-01"},
        ])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-036"]
        assert len(fails) > 0


class TestCategory7CarryForward:
    """RPS-038 - RPS-042: Carry Forward."""

    def test_opening_balance_mismatch_with_prev_closing(self, validator):
        df = make_df([
            {"loan_id": "L1", "installment_number": 1, "opening_balance": 100000.0, "principal": 10000.0, "closing_balance": 90000.0},
            {"loan_id": "L1", "installment_number": 2, "opening_balance": 85000.0, "principal": 10000.0, "closing_balance": 75000.0},
        ])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-039"]
        assert len(fails) > 0


class TestCategory8BilledFlag:
    """RPS-043 - RPS-046: Billed Flag."""

    def test_billed_true_missing_date(self, validator):
        df = make_df([{"loan_id": "L1", "billed_flag": "true", "billed_date": None}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-044"]
        assert len(fails) > 0

    def test_billed_false_provided_date(self, validator):
        df = make_df([{"loan_id": "L1", "billed_flag": "false", "billed_date": "2024-01-01"}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-046"]
        assert len(fails) > 0


class TestCategory9TDS:
    """RPS-047 - RPS-049: TDS."""

    def test_tds_rate_zero_positive_amount(self, validator):
        df = make_df([{"loan_id": "L1", "tds_rate": 0, "tds_amount": 500.0}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-048"]
        assert len(fails) > 0


class TestCategory10Foreclosure:
    """RPS-050 - RPS-063: Foreclosure (FC)."""

    def test_fc_row_nonzero_closing_balance(self, validator):
        df = make_df([{"loan_id": "L1", "installment_indicator": "FC", "closing_balance": 50000.0}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-052"]
        assert len(fails) > 0

    def test_row_after_fc(self, validator):
        df = make_df([
            {"loan_id": "L1", "installment_number": 1, "installment_indicator": "FC", "closing_balance": 0.0},
            {"loan_id": "L1", "installment_number": 2, "status": "pending"},
        ])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-053"]
        assert len(fails) > 0


class TestCategory11PartPayment:
    """RPS-064 - RPS-069: Part Payment (PP)."""

    def test_pp_negative_principal(self, validator):
        df = make_df([{"loan_id": "L1", "installment_indicator": "PP", "principal": -1000.0}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-068"]
        assert len(fails) > 0


class TestCategory12FinalBalance:
    """RPS-070 - RPS-074: Final Balance."""

    def test_last_normal_nonzero_closing_balance(self, validator):
        df = make_df([{"loan_id": "L1", "installment_number": 1, "closing_balance": 5000.0}])
        results = validator.validate(df)
        fails = [r for r in results if r.rule_id == "RPS-071"]
        assert len(fails) > 0


class TestActualExcelFile:
    """Integration test: Run validator against the actual Repayment Schedule Excel file."""

    EXCEL_FILE = r"C:\Users\satyam.raj_synoriq\Downloads\Copy of 13_repayment_schedule_202312211336.xlsx"

    def test_actual_repayment_schedule_file(self, validator):
        if not os.path.exists(self.EXCEL_FILE):
            pytest.skip("Actual repayment schedule Excel file not found.")

        xl = pd.ExcelFile(self.EXCEL_FILE)
        df = xl.parse(xl.sheet_names[0])
        assert len(df) > 0, "Excel sheet has no data."

        results = validator.validate(df)
        assert isinstance(results, list)
        print(f"\n[Actual Repayment Schedule Excel] Loaded {len(df)} rows, Total Findings: {len(results)}")
