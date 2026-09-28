"""
Unit Tests for Loan-Level Impact and Affected Loans Summary.

Covers:
1. 1 finding = 1 affected row, 1 affected loan
2. Multiple findings for same loan = multiple rows, 1 affected loan
3. 100 findings across 18 loans = 100 rows, 18 unique affected loans (COUNT DISTINCT)
4. Same loan affected by multiple rules = counted once in overall unique affected loans
5. Different loans with same rule = counted as distinct loans for that rule
6. Sheet with loan_id but no loan_application_number resolves via mapping
7. No mapping available -> loan marked as 'Unresolved' (never guessed)
8. Excel report generation with Affected Loans tab intact and backwards compatible
"""

import pandas as pd
import pytest
from openpyxl import load_workbook

from src.core.models import ValidationResult, ValidationSummary, Severity, Status
from src.core.loan_impact import (
    LoanIdentificationEngine,
    LoanFindingImpact,
    LoanImpactSummary,
    RuleLoanSummary
)
from src.core.report_generator import generate_excel_report, generate_multi_sheet_excel_report


def test_single_finding_single_loan():
    """1 finding -> 1 affected row, 1 affected loan."""
    df = pd.DataFrame({
        "loan_application_number": ["APP001", "APP002", "APP003"],
        "interest_rate": [12.5, "INVALID", 15.0]
    })
    results = [
        ValidationResult(
            rule_id="RPS-001",
            module="Loan Application",
            field="interest_rate",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="Interest rate must be numeric",
            row_number=3,
            actual_value="INVALID",
            expected_value="Number"
        )
    ]
    enriched, summary = LoanIdentificationEngine.analyze_impact(results, source_df=df, default_module="Loan Application")

    assert len(enriched) == 1
    assert enriched[0].loan_application_number == "APP002"
    assert summary.total_findings == 1
    assert summary.total_affected_rows == 1
    assert summary.total_unique_affected_loans == 1
    assert summary.resolved_affected_loans_count == 1
    assert summary.unresolved_findings_count == 0


def test_multiple_findings_same_loan():
    """Multiple findings for same loan = multiple rows, 1 affected loan."""
    df = pd.DataFrame({
        "loan_application_number": ["APP001", "APP001", "APP001"],
        "installment_no": [1, 2, 3],
        "due_date": ["2026-01-01", "bad_date", "bad_date_2"]
    })
    results = [
        ValidationResult(
            rule_id="RPS-010",
            module="Repayment Schedule",
            field="due_date",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="Due date invalid",
            row_number=2,
            actual_value="bad_date",
            expected_value="YYYY-MM-DD"
        ),
        ValidationResult(
            rule_id="RPS-010",
            module="Repayment Schedule",
            field="due_date",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="Due date invalid",
            row_number=3,
            actual_value="bad_date_2",
            expected_value="YYYY-MM-DD"
        ),
        ValidationResult(
            rule_id="RPS-015",
            module="Repayment Schedule",
            field="installment_no",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="Installment sequence gap",
            row_number=4,
            actual_value="3",
            expected_value="Sequential"
        )
    ]
    enriched, summary = LoanIdentificationEngine.analyze_impact(results, source_df=df, default_module="Repayment Schedule")

    assert summary.total_findings == 3
    assert summary.total_affected_rows == 3
    assert summary.total_unique_affected_loans == 1
    assert summary.unique_failed_rules_count == 2
    assert summary.resolved_affected_loans_count == 1
    assert summary.unresolved_findings_count == 0


def test_hundred_findings_across_eighteen_loans():
    """100 findings across 18 unique loans = 100 rows, 18 unique affected loans."""
    # Create 100 rows spread across 18 unique loan applications
    loan_apps = [f"APP_{i % 18:03d}" for i in range(100)]
    df = pd.DataFrame({
        "loan_application_number": loan_apps,
        "amount": [-100] * 100
    })
    results = [
        ValidationResult(
            rule_id="RPS-062",
            module="Repayment Schedule",
            field="amount",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="Amount must be positive",
            row_number=idx + 2,
            actual_value="-100",
            expected_value="> 0"
        )
        for idx in range(100)
    ]
    enriched, summary = LoanIdentificationEngine.analyze_impact(results, source_df=df, default_module="Repayment Schedule")

    assert summary.total_findings == 100
    assert summary.total_affected_rows == 100
    assert summary.total_unique_affected_loans == 18
    assert summary.resolved_affected_loans_count == 18
    assert summary.unresolved_findings_count == 0
    assert len(summary.rule_summaries) == 1
    assert summary.rule_summaries[0].affected_loans_count == 18
    assert summary.rule_summaries[0].affected_rows_count == 100


def test_same_loan_multiple_rules_deduplicated():
    """Same loan affected by multiple rules -> counted once in overall unique affected loans."""
    df = pd.DataFrame({
        "loan_application_number": ["APP100"],
        "rate": [-5],
        "tenure": [0]
    })
    results = [
        ValidationResult(
            rule_id="RULE-1",
            module="Loans",
            field="rate",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="Negative rate",
            row_number=2,
            actual_value="-5",
            expected_value=">0"
        ),
        ValidationResult(
            rule_id="RULE-2",
            module="Loans",
            field="tenure",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="Zero tenure",
            row_number=2,
            actual_value="0",
            expected_value=">0"
        )
    ]
    enriched, summary = LoanIdentificationEngine.analyze_impact(results, source_df=df, default_module="Loans")

    assert summary.total_findings == 2
    assert summary.total_affected_rows == 1  # 2 findings on the exact same row
    assert summary.total_unique_affected_loans == 1
    assert summary.unique_failed_rules_count == 2


def test_different_loans_same_rule():
    """Different loans affected by same rule -> counted as distinct loans for that rule."""
    df = pd.DataFrame({
        "loan_application_number": ["APP01", "APP02", "APP03"],
        "status": ["INVALID", "INVALID", "INVALID"]
    })
    results = [
        ValidationResult(
            rule_id="RULE-COMMON",
            module="Loans",
            field="status",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="Status invalid",
            row_number=i + 2,
            actual_value="INVALID",
            expected_value="ACTIVE"
        )
        for i in range(3)
    ]
    enriched, summary = LoanIdentificationEngine.analyze_impact(results, source_df=df, default_module="Loans")

    assert summary.total_unique_affected_loans == 3
    rule_sum = summary.rule_summaries[0]
    assert rule_sum.affected_loans_count == 3
    assert set(rule_sum.affected_loans_list) == {"APP01", "APP02", "APP03"}


def test_loan_id_resolves_to_application_number_via_mapping():
    """Sheet with loan_id but no loan_application_number resolves via mapping."""
    loans_master_df = pd.DataFrame({
        "loan_id": ["L901", "L902"],
        "loan_application_number": ["APP-GLOBAL-901", "APP-GLOBAL-902"]
    })
    collateral_df = pd.DataFrame({
        "loan_id": ["L901"],
        "collateral_value": [-5000]
    })
    results = [
        ValidationResult(
            rule_id="COL-005",
            module="Collateral",
            field="collateral_value",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="Collateral value must be > 0",
            row_number=2,
            actual_value="-5000",
            expected_value="> 0"
        )
    ]
    workbook_dfs = {
        "Loans": loans_master_df,
        "Collateral": collateral_df
    }

    enriched, summary = LoanIdentificationEngine.analyze_impact(
        results,
        source_df=collateral_df,
        workbook_dfs=workbook_dfs,
        default_module="Collateral"
    )

    assert len(enriched) == 1
    assert enriched[0].loan_id == "L901"
    assert enriched[0].loan_application_number == "APP-GLOBAL-901"
    assert enriched[0].canonical_loan_key == "APP-GLOBAL-901"
    assert summary.total_unique_affected_loans == 1
    assert summary.resolved_affected_loans_count == 1
    assert summary.unresolved_findings_count == 0


def test_unresolved_loan_when_no_identifier_or_mapping():
    """Sheet with neither loan_id nor loan_application_number marks finding as 'Unresolved' (never guessed)."""
    random_df = pd.DataFrame({
        "fee_code": ["FEE_01"],
        "rate": ["ABC"]
    })
    results = [
        ValidationResult(
            rule_id="FEE-001",
            module="Charges",
            field="rate",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="Rate must be numeric",
            row_number=2,
            actual_value="ABC",
            expected_value="Numeric"
        )
    ]
    enriched, summary = LoanIdentificationEngine.analyze_impact(results, source_df=random_df, default_module="Charges")

    assert len(enriched) == 1
    assert enriched[0].loan_id == "Unresolved"
    assert enriched[0].loan_application_number == "Unresolved"
    assert enriched[0].canonical_loan_key == "Unresolved"
    assert summary.total_unique_affected_loans == 0
    assert summary.resolved_affected_loans_count == 0
    assert summary.unresolved_findings_count == 1


def test_excel_export_with_affected_loans_tab():
    """Report generator adds 'Affected Loans' sheet without breaking existing sheets."""
    df = pd.DataFrame({
        "loan_application_number": ["APP100"],
        "amount": [-10]
    })
    results = [
        ValidationResult(
            rule_id="RPS-001",
            module="Loans",
            field="amount",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="Amount must be positive",
            row_number=2,
            actual_value="-10",
            expected_value="> 0"
        )
    ]
    enriched, summary_impact = LoanIdentificationEngine.analyze_impact(results, source_df=df, default_module="Loans")

    affected_loans_data = [
        {
            "Rule ID": "RPS-001",
            "Module": "Loans",
            "Loan ID": "Unresolved",
            "Loan Application Number": "APP100",
            "Finding Count": 1,
            "Error Rows": "2",
            "Severity": "ERROR"
        }
    ]

    val_summary = ValidationSummary.from_results(
        module="Loans",
        total_records=1,
        rules_checked_count=5,
        results=results
    )

    excel_bytes = generate_excel_report(val_summary, results, affected_loans_data=affected_loans_data)
    wb = load_workbook(excel_bytes)

    assert "Summary Dashboard" in wb.sheetnames
    assert "Validation Details" in wb.sheetnames
    assert "Affected Loans" in wb.sheetnames

    ws_loans = wb["Affected Loans"]
    assert ws_loans["A4"].value == "Rule ID"
    assert ws_loans["A5"].value == "RPS-001"
    assert ws_loans["D5"].value == "APP100"
