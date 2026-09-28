"""
Comprehensive Unit Tests for SynoFin Migration Audit Assistant.

Verifies:
1. "Hello" gets a valid greeting.
2. "What can you do?" works.
3. Module rule question works.
4. Rule ID explanation works.
5. Current audit summary uses actual counts.
6. Specific loan question uses actual findings.
7. Follow-up question retains context.
8. Unknown rule does not hallucinate.
9. Missing audit data is handled correctly.
10. Large audit context is filtered rather than sending all rows.
11. Existing validator tests remain unchanged and passing.
"""

import pytest
import pandas as pd

from src.core.models import ValidationResult, ValidationSummary, Severity, Status
from src.assistant.service import AuditAssistant, AuditContext, FALLBACK_MESSAGE
from src.assistant.knowledge import RuleKnowledgeBase
from src.core.loan_impact import LoanImpactSummary
from src.modules.loan_application.validator import LoanApplicationValidator


def create_mock_context():
    results = [
        ValidationResult(
            rule_id="LA-001",
            module="Loan Application",
            field="loan_id",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="loan_id cannot be blank.",
            row_number=2,
            actual_value="EMPTY",
            expected_value="Integer loan ID"
        ),
        ValidationResult(
            rule_id="RPS-018",
            module="Repayment Schedule",
            field="status",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="status=paid requires received_amount = installment_amount",
            row_number=3,
            actual_value="paid",
            expected_value="received_amount = installment_amount"
        ),
        ValidationResult(
            rule_id="COLL-020",
            module="Collateral",
            field="region",
            severity=Severity.WARNING,
            status=Status.FAIL,
            description="region lowercase one of north/south/east/west where populated",
            row_number=2,
            actual_value="central",
            expected_value="north/south/east/west"
        )
    ]

    source_df = pd.DataFrame([
        {"loan_id": "LN-99901", "status": "pending", "region": "central"},
        {"loan_id": "LN-99902", "status": "paid", "region": "north"},
    ])

    summary = ValidationSummary.from_results(
        module="Loan Application",
        total_records=2,
        rules_checked_count=25,
        results=results
    )

    return AuditContext(
        summary=summary,
        results=results,
        source_df=source_df,
        module_name="Loan Application"
    )


def create_rule_impact_context():
    results = [
        ValidationResult(
            rule_id="RPS-009",
            module="Repayment Schedule",
            field="status",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="status=paid requires received_amount = installment_amount",
            row_number=2,
            actual_value="paid",
            expected_value="received_amount = installment_amount"
        ),
        ValidationResult(
            rule_id="RPS-009",
            module="Repayment Schedule",
            field="status",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="status=paid requires received_amount = installment_amount",
            row_number=3,
            actual_value="paid",
            expected_value="received_amount = installment_amount"
        ),
        ValidationResult(
            rule_id="LA-001",
            module="Loan Application",
            field="loan_id",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="loan_id cannot be blank.",
            row_number=4,
            actual_value="EMPTY",
            expected_value="Integer loan ID"
        ),
    ]
    source_df = pd.DataFrame([
        {"loan_id": "LN-1001", "status": "paid", "loan_application_number": "APP-1001"},
        {"loan_id": "LN-1001", "status": "paid", "loan_application_number": "APP-1001"},
        {"loan_id": "LN-2002", "status": "pending", "loan_application_number": "APP-2002"},
    ])
    summary = ValidationSummary.from_results(
        module="Repayment Schedule",
        total_records=3,
        rules_checked_count=25,
        results=results
    )
    loan_impact = LoanImpactSummary(
        total_findings=3,
        total_affected_rows=3,
        total_unique_affected_loans=2,
        unique_failed_rules_count=2,
        resolved_affected_loans_count=2,
        unresolved_findings_count=0,
        rule_summaries=[],
        loan_details_by_rule={},
        all_affected_loans=[
            {"Loan ID": "LN-1001", "Loan Application Number": "APP-1001", "Module": "Repayment Schedule", "Total Findings": 2, "Rules Violated": "RPS-009", "Affected Rows": "2, 3"},
            {"Loan ID": "LN-2002", "Loan Application Number": "APP-2002", "Module": "Loan Application", "Total Findings": 1, "Rules Violated": "LA-001", "Affected Rows": "4"},
        ],
    )
    return AuditContext(summary=summary, results=results, source_df=source_df, module_name="Repayment Schedule", loan_impact=loan_impact)


# ---------------------------------------------------------------------------
# Test 1: "Hello" gets a valid greeting
# ---------------------------------------------------------------------------
def test_greeting():
    assistant = AuditAssistant()
    reply = assistant.ask("Hello")
    assert "SynoFin Migration Audit Assistant" in reply
    assert "What would you like to check?" in reply


# ---------------------------------------------------------------------------
# Test 2: "What can you do?" works
# ---------------------------------------------------------------------------
def test_capabilities():
    assistant = AuditAssistant()
    reply = assistant.ask("What can you do?")
    assert "Explore Validation Rules" in reply
    assert "Rule Explanations" in reply
    assert "Audit Summary" in reply


def test_capabilities_intent_hindi_variation():
    assistant = AuditAssistant()
    reply = assistant.ask("tumhe kya kya aata hai")
    assert "Migration template structure" in reply or "validation rules" in reply.lower()


def test_capabilities_intent_what_do_you_know():
    assistant = AuditAssistant()
    reply = assistant.ask("what do you know")
    assert "Migration template" in reply or "validation rules" in reply.lower()


def test_template_intent_cust_idx_hindi():
    assistant = AuditAssistant()
    reply = assistant.ask("cust_idx kya hai?")
    assert "Column:" in reply
    assert "cust_idx" in reply


def test_template_intent_repayment_status_question():
    assistant = AuditAssistant()
    reply = assistant.ask("what is repayment_schedule.status?")
    assert "repayment_schedule" in reply.lower()
    assert "status" in reply.lower()


def test_validation_intent_hindi_module_lookup():
    assistant = AuditAssistant()
    reply = assistant.ask("repayment schedule mein kaunse validations hain?")
    assert "RPS-001" in reply or "Repayment Schedule" in reply


def test_validation_intent_registry_question():
    assistant = AuditAssistant()
    reply = assistant.ask("what validations are applied to repayment_schedule?")
    assert "RPS-001" in reply or "Repayment Schedule" in reply


def test_unknown_intent_does_not_route_to_template():
    assistant = AuditAssistant()
    reply = assistant.ask("this is a completely unsupported test question for nothing")
    assert "I couldn't determine which migration information you're asking about" in reply


def test_repeated_loan_lookup_uses_session_local_cache_and_missing_loan_is_graceful():
    assistant = AuditAssistant(context=create_mock_context())
    assert hasattr(assistant.context, "get_loan_lookup_index")
    assert hasattr(assistant, "_loan_match_cache")

    first = assistant._find_loan_matches("LN-99901")
    second = assistant._find_loan_matches("LN-99901")
    assert first == second
    assert len(first) >= 1

    missing_reply = assistant.ask("Show issues for loan MISSING-999")
    assert "No audit findings were found" in missing_reply


# ---------------------------------------------------------------------------
# Test 3: Module rule question works (even without file upload)
# ---------------------------------------------------------------------------
def test_module_rules_query():
    assistant = AuditAssistant()  # No context / no file
    reply = assistant.ask("What rules are applied to Customer?")
    assert "Customer" in reply
    assert "Total Registered Rules:" in reply
    assert "CUST_TC" in reply


# ---------------------------------------------------------------------------
# Test 4: Rule ID explanation works
# ---------------------------------------------------------------------------
def test_rule_id_explanation():
    assistant = AuditAssistant()
    reply = assistant.ask("What does RPS-018 mean?")
    assert "RPS-018" in reply
    assert "Repayment Schedule" in reply
    assert "status=paid requires received_amount = installment_amount" in reply


# ---------------------------------------------------------------------------
# Test 5: Current audit summary uses actual counts
# ---------------------------------------------------------------------------
def test_audit_summary_actual_counts():
    ctx = create_mock_context()
    assistant = AuditAssistant(ctx)
    reply = assistant.ask("Summarize this audit")
    assert "Loan Application" in reply
    assert "Records Audited:** 2" in reply
    assert "Critical Errors:** 2" in reply
    assert "Advisory Warnings:** 1" in reply


def test_audit_summary_counts_questions_use_current_findings():
    ctx = create_mock_context()
    assistant = AuditAssistant(ctx)
    reply = assistant.ask("How many errors are there?")
    assert "2" in reply and "Errors" in reply

    reply = assistant.ask("How many warnings are there?")
    assert "1" in reply and "Warnings" in reply

    reply = assistant.ask("Which rules are failing?")
    assert "LA-001" in reply or "RPS-018" in reply or "COLL-020" in reply


# ---------------------------------------------------------------------------
# Test 6: Specific loan question uses actual findings
# ---------------------------------------------------------------------------
def test_specific_loan_analysis():
    ctx = create_mock_context()
    assistant = AuditAssistant(ctx)
    reply = assistant.ask("Show all issues for loan LN-99901")
    assert "LN-99901" in reply
    assert "LA-001" in reply
    assert "RPS-018" not in reply  # RPS-018 belongs to LN-99902


# ---------------------------------------------------------------------------
# Test 7: Follow-up question retains context
# ---------------------------------------------------------------------------
def test_follow_up_context():
    ctx = create_mock_context()
    assistant = AuditAssistant(ctx)
    assistant.ask("Show all issues for loan LN-99901")
    follow_up_reply = assistant.ask("How do I fix it?")
    assert "Fix Guidance" in follow_up_reply
    assert "LA-001" in follow_up_reply


# ---------------------------------------------------------------------------
# Test 8: Unknown rule does not hallucinate
# ---------------------------------------------------------------------------
def test_unknown_rule_fallback():
    assistant = AuditAssistant()
    reply = assistant.ask("Explain rule FAKE-999")
    assert reply == FALLBACK_MESSAGE


# ---------------------------------------------------------------------------
# Test 9: Missing audit data is handled correctly
# ---------------------------------------------------------------------------
def test_missing_audit_data_handling():
    assistant = AuditAssistant()  # empty context
    reply = assistant.ask("Summarize this audit")
    assert "No audit results are currently available" in reply


# ---------------------------------------------------------------------------
# Test 10: Large audit context is filtered rather than sending all rows
# ---------------------------------------------------------------------------
def test_large_audit_context_filtered():
    # 500 records failing RPS-007
    large_results = [
        ValidationResult(
            rule_id="RPS-007",
            module="Repayment Schedule",
            field="installment_amount",
            severity=Severity.ERROR,
            status=Status.FAIL,
            description="installment_amount must equal principal + interest",
            row_number=i + 2,
            actual_value="5000",
            expected_value="principal + interest"
        )
        for i in range(500)
    ]
    summary = ValidationSummary.from_results(
        module="Repayment Schedule",
        total_records=500,
        rules_checked_count=30,
        results=large_results
    )
    ctx = AuditContext(summary=summary, results=large_results, module_name="Repayment Schedule")
    assistant = AuditAssistant(ctx)

    reply = assistant.ask("Why are there errors?")
    assert "RPS-007" in reply
    assert "500" in reply
    assert "failed" in reply
    # Must NOT contain 500 individual row dumps
    assert reply.count("RPS-007") <= 5


def test_template_column_lookup_cust_idx():
    assistant = AuditAssistant()
    reply = assistant.ask("What is cust_idx?")
    assert "Column:" in reply
    assert "cust_idx" in reply
    assert "customers" in reply.lower()


def test_template_column_lookup_repayment_status_exact_sheet():
    assistant = AuditAssistant()
    reply = assistant.ask("What is repayment_schedule.status?")
    assert "repayment_schedule" in reply.lower()
    assert "status" in reply.lower()
    assert "Allowed Values:" in reply
    assert "paid" in reply.lower()


def test_template_allowed_values_lookup():
    assistant = AuditAssistant()
    reply = assistant.ask("What are the allowed values for repayment status?")
    assert "due" in reply.lower()
    assert "paid" in reply.lower()
    assert "not_due" in reply.lower()


def test_template_sheet_lookup():
    assistant = AuditAssistant()
    reply = assistant.ask("Which sheet contains bank details?")
    assert "bank_details" in reply.lower()


def test_template_relationship_lookup():
    assistant = AuditAssistant()
    reply = assistant.ask("How do I link loan records across sheets?")
    assert "loan_application_number" in reply.lower()
    assert "linking key" in reply.lower()


def test_template_readme_control_lookup():
    assistant = AuditAssistant()
    reply = assistant.ask("What is the purpose of the CONTROL sheet?")
    assert "batch control" in reply.lower() or "reconciliation" in reply.lower()


def test_template_natural_language_variation():
    assistant = AuditAssistant()
    reply = assistant.ask("status ka kya matlab hai?")
    assert "Column:" in reply
    assert "status" in reply.lower()
    assert "repayment_schedule" in reply.lower()


def test_template_unknown_column_not_defined():
    assistant = AuditAssistant()
    reply = assistant.ask("What is totally_fake_template_field_zzz?")
    assert "This information is not defined in the migration template." in reply


def test_template_unknown_question_is_rejected_without_hallucination():
    assistant = AuditAssistant()
    reply = assistant.ask("Why did loan 123 fail validation?")
    assert "template-related questions here" in reply.lower()
    assert "Validation-specific analysis" in reply


def test_validation_rules_by_module_repayment_schedule():
    assistant = AuditAssistant()
    reply = assistant.ask("What validations are applied to repayment_schedule?")
    assert "RPS-001" in reply
    assert "Repayment Schedule" in reply


def test_validation_rules_by_module_alias():
    assistant = AuditAssistant()
    reply = assistant.ask("Which rules are available for repayment schedule?")
    assert "RPS-018" in reply or "RPS-009" in reply


def test_validation_rule_by_id_lookup():
    assistant = AuditAssistant()
    reply = assistant.ask("What does rule RPS-018 check?")
    assert "RPS-018" in reply
    assert "status=paid requires received_amount = installment_amount" in reply


def test_validation_rule_severity_lookup():
    assistant = AuditAssistant()
    reply = assistant.ask("What is the severity of RPS-018?")
    assert "Severity:" in reply
    assert "ERROR" in reply


def test_validation_rule_keyword_lookup():
    assistant = AuditAssistant()
    reply = assistant.ask("Which rule checks closing balance?")
    assert "RPS-009" in reply or "RPS-016" in reply


def test_validation_rule_hindi_variation():
    assistant = AuditAssistant()
    reply = assistant.ask("repayment schedule mein kaunse validations hain?")
    assert "RPS-001" in reply or "RPS-018" in reply or "Repayment Schedule" in reply


def test_unknown_rule_metadata_fallback():
    assistant = AuditAssistant()
    reply = assistant.ask("What does rule FAKE-999 check?")
    assert reply == FALLBACK_MESSAGE


# ---------------------------------------------------------------------------
# Test 11: Existing validator tests remain unchanged and passing
# ---------------------------------------------------------------------------
def test_rule_specific_findings_query():
    ctx = create_rule_impact_context()
    assistant = AuditAssistant(ctx)
    reply = assistant.ask("Show findings for RPS-009.")
    assert "RPS-009" in reply
    assert "LN-1001" in reply or "APP-1001" in reply
    assert "Row Number" in reply or "Row" in reply


def test_rule_specific_affected_loans_query():
    ctx = create_rule_impact_context()
    assistant = AuditAssistant(ctx)
    reply = assistant.ask("Which loans failed RPS-009?")
    assert "LN-1001" in reply
    assert "1 loan" in reply.lower() or "1" in reply


def test_total_affected_loans_query():
    ctx = create_rule_impact_context()
    assistant = AuditAssistant(ctx)
    reply = assistant.ask("How many loans are affected?")
    assert "2" in reply and "affected" in reply.lower()


def test_affected_loan_count_from_findings_without_precomputed_loan_impact():
    ctx = create_mock_context()
    ctx.loan_impact = None
    assistant = AuditAssistant(ctx)
    reply = assistant.ask("How many loans are affected?")
    assert "2" in reply and "affected" in reply.lower()
    assert "NameError" not in reply


def test_rule_specific_affected_loan_count_query():
    ctx = create_rule_impact_context()
    assistant = AuditAssistant(ctx)
    reply = assistant.ask("How many loans failed RPS-009?")
    assert "1" in reply and "RPS-009" in reply


def test_rule_exists_zero_findings_query():
    ctx = create_rule_impact_context()
    assistant = AuditAssistant(ctx)
    reply = assistant.ask("Show findings for RPS-004.")
    assert "no findings" in reply.lower() or "0" in reply


def test_unknown_rule_query_uses_existing_fallback():
    ctx = create_rule_impact_context()
    assistant = AuditAssistant(ctx)
    reply = assistant.ask("Show findings for FAKE-999.")
    assert reply == FALLBACK_MESSAGE or "not defined" in reply.lower() or "no findings" in reply.lower()


def test_no_audit_context_affected_loan_count():
    assistant = AuditAssistant()
    reply = assistant.ask("How many loans are affected?")
    assert "No audit results are currently available" in reply or "No audit data" in reply


def test_zero_findings_affected_loan_count():
    summary = ValidationSummary(module="Repayment Schedule", total_records=3, total_rules_checked=10, total_passed=10, total_failed=0, total_errors=0, total_warnings=0)
    ctx = AuditContext(summary=summary, results=[], source_df=pd.DataFrame([{"loan_id": "LN-1"}]), module_name="Repayment Schedule")
    assistant = AuditAssistant(ctx)
    reply = assistant.ask("How many loans are affected?")
    assert "0" in reply


def create_cross_sheet_context():
    customers = pd.DataFrame([
        {"loan_application_number": "APP-1001", "cust_idx": "C-01", "customer_name": "Alice Kumar"}
    ])
    bank_details = pd.DataFrame([
        {"loan_application_number": "APP-1001", "bank_idx": "B-01", "ifsc": "ICIC0001234", "bank_name": "ICICI"}
    ])
    nach_detail = pd.DataFrame([
        {"loan_application_number": "APP-1001", "cust_idx": "C-01", "bank_idx": "B-01", "umrn": "UMRN-001"}
    ])
    repayment_schedule = pd.DataFrame([
        {"loan_application_number": "APP-1001", "status": "paid", "received_amount": 250.00}
    ])
    charges = pd.DataFrame([
        {"loan_application_number": "APP-1001", "charge_id": "CH-01", "charge_amount": 200.00}
    ])
    disbursal_breakup = pd.DataFrame([
        {"loan_application_number": "APP-1001", "disbursal_number": "D-01", "disbursal_amount": 1200.00}
    ])
    receipts = pd.DataFrame([
        {"loan_application_number": "APP-1001", "receipt_id": "R-01", "amount": 300.00, "repayment_schedule_id": "RS-01"}
    ])
    excess_money = pd.DataFrame([
        {"receipt_id": "R-01", "amount": 50.00}
    ])
    ctx = AuditContext(
        summary=ValidationSummary(module="Loan Application", total_records=1, total_rules_checked=10, total_passed=9, total_failed=1, total_errors=1, total_warnings=0),
        results=[],
        source_df=pd.DataFrame([{"loan_application_number": "APP-1001", "loan_id": "LN-1001"}]),
        module_name="Loan Application"
    )
    ctx.sheet_dfs = {
        "customers": customers,
        "bank_details": bank_details,
        "nach_detail": nach_detail,
        "repayment_schedule": repayment_schedule,
        "charges": charges,
        "disbursal_breakup": disbursal_breakup,
        "disbursal_schedule": pd.DataFrame([{"loan_application_number": "APP-1001", "disbursal_number": "D-01", "amount": 1200.00}]),
        "receipts": receipts,
        "excess_money": excess_money,
    }
    return ctx


def test_cross_sheet_loan_summary_uses_current_workbook_data():
    ctx = create_cross_sheet_context()
    assistant = AuditAssistant(ctx)
    reply = assistant.ask("Show data for loan APP-1001 across all sheets.")
    assert "APP-1001" in reply
    assert "Customers" in reply or "customers" in reply
    assert "Bank Details" in reply or "bank_details" in reply.lower()
    assert "Repayment" in reply or "repayment_schedule" in reply.lower()


def test_cross_sheet_customer_lookup():
    ctx = create_cross_sheet_context()
    assistant = AuditAssistant(ctx)
    reply = assistant.ask("Who is the customer for loan APP-1001?")
    assert "Alice Kumar" in reply


def test_cross_sheet_bank_lookup():
    ctx = create_cross_sheet_context()
    assistant = AuditAssistant(ctx)
    reply = assistant.ask("Show bank details for loan APP-1001.")
    assert "ICIC0001234" in reply or "ICICI" in reply


def test_cross_sheet_reconciliation_receipts_vs_repayment():
    ctx = create_cross_sheet_context()
    assistant = AuditAssistant(ctx)
    reply = assistant.ask("Compare receipts with repayment schedule.")
    assert "APP-1001" in reply or "receipts" in reply.lower() or "reconciliation" in reply.lower()
    assert "Mismatch" in reply or "MATCH" in reply or "difference" in reply.lower()


def test_cross_sheet_reconciliation_summary_for_loan():
    ctx = create_cross_sheet_context()
    assistant = AuditAssistant(ctx)
    reply = assistant.ask("Compare receipts and repayment schedule for loan APP-1001.")
    assert "APP-1001" in reply
    assert "Difference" in reply or "Status" in reply or "reconciliation" in reply.lower()


def test_validator_behavior_unchanged():
    v = LoanApplicationValidator()
    df = pd.DataFrame([{"loan_id": None}])
    res = v.validate(df)
    assert any(r.status == Status.FAIL for r in res)
