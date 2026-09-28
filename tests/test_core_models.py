"""
Unit tests for core models (Severity, Status, ValidationResult, ValidationSummary).
"""

from src.core.models import Severity, Status, ValidationResult, ValidationSummary


def test_validation_result_to_dict():
    """Test ValidationResult dictionary conversion."""
    res = ValidationResult(
        rule_id="TEST_001",
        module="TestModule",
        field="TestField",
        severity=Severity.ERROR,
        status=Status.FAIL,
        description="Missing mandatory field",
        row_number=5,
        actual_value="EMPTY",
        expected_value="Non-empty"
    )
    d = res.to_dict()

    assert d["Rule ID"] == "TEST_001"
    assert d["Module"] == "TestModule"
    assert d["Field/Column"] == "TestField"
    assert d["Severity"] == "ERROR"
    assert d["Status"] == "FAIL"
    assert d["Description"] == "Missing mandatory field"
    assert d["Row Number"] == 5
    assert d["Actual Value"] == "EMPTY"
    assert d["Expected Value"] == "Non-empty"


def test_validation_summary_from_results():
    """Test ValidationSummary metric calculations."""
    results = [
        ValidationResult("R1", "Mod", "Col1", Severity.ERROR, Status.FAIL, "Err1", 2),
        ValidationResult("R2", "Mod", "Col2", Severity.WARNING, Status.FAIL, "Warn1", 3),
        ValidationResult("R3", "Mod", "Col3", Severity.ERROR, Status.PASS, "Pass1", 4),
    ]

    summary = ValidationSummary.from_results(
        module="Mod",
        total_records=10,
        rules_checked_count=5,
        results=results
    )

    assert summary.module == "Mod"
    assert summary.total_records == 10
    assert summary.total_rules_checked == 5
    assert summary.total_passed == 1
    assert summary.total_failed == 2
    assert summary.total_errors == 1
    assert summary.total_warnings == 1
    assert summary.pass_percentage == 33.33
