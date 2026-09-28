"""
Data models and schemas for Excel Migration Validator.
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(str, Enum):
    """Severity levels for validation findings."""
    ERROR = "ERROR"
    WARNING = "WARNING"


class Status(str, Enum):
    """Validation rule evaluation status."""
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass
class ValidationResult:
    """
    Standardized Validation Result representation.
    
    Attributes:
        rule_id: Unique rule identifier (e.g., CUST_001).
        module: Migration module name (e.g., Customer, Loan Application).
        field: Target Excel column / field name.
        severity: Severity level (ERROR or WARNING).
        status: PASS or FAIL status.
        description: Rule description / human readable error context.
        row_number: 1-indexed Excel row number (header is row 1, data starts row 2).
                    Set to None for sheet-level / structural findings.
        actual_value: The value found in the Excel cell.
        expected_value: Expected value or description of expected format/type.
    """
    rule_id: str
    module: str
    field: str
    severity: Severity
    status: Status
    description: str
    row_number: Optional[int] = None
    actual_value: Optional[Any] = None
    expected_value: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to a plain dictionary format suitable for DataFrames."""
        return {
            "Rule ID": self.rule_id,
            "Module": self.module,
            "Field/Column": self.field,
            "Severity": self.severity.value if isinstance(self.severity, Severity) else str(self.severity),
            "Status": self.status.value if isinstance(self.status, Status) else str(self.status),
            "Description": self.description,
            "Row Number": self.row_number if self.row_number is not None else "N/A",
            "Actual Value": "" if self.actual_value is None else str(self.actual_value),
            "Expected Value": "" if self.expected_value is None else str(self.expected_value),
        }


@dataclass
class ValidationSummary:
    """
    Aggregated summary metrics for a validation execution run.
    """
    module: str
    total_records: int
    total_rules_checked: int
    total_passed: int
    total_failed: int
    total_errors: int
    total_warnings: int

    @property
    def pass_percentage(self) -> float:
        """Calculate percentage of passing results."""
        total_evaluations = self.total_passed + self.total_failed
        if total_evaluations == 0:
            return 100.0
        return round((self.total_passed / total_evaluations) * 100, 2)

    @classmethod
    def from_results(cls, module: str, total_records: int, rules_checked_count: int, results: List[ValidationResult]) -> "ValidationSummary":
        """Compute summary metrics from a list of ValidationResult objects."""
        passed_count = sum(1 for r in results if r.status == Status.PASS)
        failed_count = sum(1 for r in results if r.status == Status.FAIL)
        errors_count = sum(1 for r in results if r.status == Status.FAIL and r.severity == Severity.ERROR)
        warnings_count = sum(1 for r in results if r.status == Status.FAIL and r.severity == Severity.WARNING)

        return cls(
            module=module,
            total_records=total_records,
            total_rules_checked=rules_checked_count,
            total_passed=passed_count,
            total_failed=failed_count,
            total_errors=errors_count,
            total_warnings=warnings_count,
        )
