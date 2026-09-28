"""
Disbursal Schedule Migration Module Validator.

Business Rules:
DS-001: loan_application_number mandatory
DS-002: disbursal_number mandatory and integer/numeric >= 1
DS-003: disbursal_amount mandatory and numeric > 0
DS-004: adjusted_amount numeric >= 0 when present
DS-005: net_disbursed_amount mandatory and numeric > 0
DS-006: net_disbursed_amount must equal disbursal_amount - adjusted_amount (tolerance 1.0)
DS-007: payment_date valid date format (YYYY-MM-DD, etc.)
DS-008: disbursal_status must be in allowed list: disbursed, partially_disbursed, pending, cancelled
DS-009: Composite unique key (loan_application_number + disbursal_number)
"""

from datetime import datetime, date
import math
from typing import List, Optional, Any, Dict
import pandas as pd

from src.core.base import BaseValidator, ValidationRule
from src.core.models import ValidationResult, Severity, Status
from src.core.registry import registry
from src.core.utils import is_blank


class DisbursalScheduleValidator(BaseValidator):
    ALLOWED_STATUSES = {"disbursed", "partially_disbursed", "pending", "cancelled"}

    MANDATORY_COLS = [
        "loan_application_number",
        "disbursal_number",
        "disbursal_amount",
        "net_disbursed_amount",
        "payment_date",
        "disbursal_status",
    ]

    @property
    def module_name(self) -> str:
        return "Disbursal Schedule"

    @property
    def required_columns(self) -> List[str]:
        return self.MANDATORY_COLS

    def get_rules_metadata(self) -> List[ValidationRule]:
        return [
            ValidationRule("DS-001", "Disbursal Schedule", "loan_application_number", "loan_application_number is mandatory", Severity.ERROR),
            ValidationRule("DS-002", "Disbursal Schedule", "disbursal_number", "disbursal_number is mandatory and numeric >= 1", Severity.ERROR),
            ValidationRule("DS-003", "Disbursal Schedule", "disbursal_amount", "disbursal_amount is mandatory and > 0", Severity.ERROR),
            ValidationRule("DS-004", "Disbursal Schedule", "adjusted_amount", "adjusted_amount must be numeric >= 0", Severity.ERROR),
            ValidationRule("DS-005", "Disbursal Schedule", "net_disbursed_amount", "net_disbursed_amount is mandatory and > 0", Severity.ERROR),
            ValidationRule("DS-006", "Disbursal Schedule", "net_disbursed_amount", "net_disbursed_amount must equal disbursal_amount - adjusted_amount", Severity.ERROR),
            ValidationRule("DS-007", "Disbursal Schedule", "payment_date", "payment_date must be a valid date", Severity.ERROR),
            ValidationRule("DS-008", "Disbursal Schedule", "disbursal_status", "disbursal_status must be in allowed list", Severity.ERROR),
            ValidationRule("DS-009", "Disbursal Schedule", "loan_application_number+disbursal_number", "Duplicate disbursal_number for the same loan", Severity.ERROR),
        ]

    def _get_col(self, col: str, df: pd.DataFrame) -> Optional[str]:
        mapping = {str(c).strip().lower(): c for c in df.columns}
        return mapping.get(col.lower())

    def _to_float(self, val: Any) -> Optional[float]:
        if is_blank(val):
            return None
        try:
            f = float(str(val).replace(",", "").strip())
            return None if math.isnan(f) else f
        except (ValueError, TypeError):
            return None

    def _parse_date(self, val: Any) -> bool:
        if is_blank(val):
            return False
        if isinstance(val, (pd.Timestamp, datetime, date)):
            return True
        val_str = str(val).strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
            try:
                datetime.strptime(val_str, fmt)
                return True
            except ValueError:
                pass
        return False

    def _add(self, results: List[ValidationResult], rule_id: str, field: str,
             row_num: int, actual: Any, expected: str, desc: str,
             severity: Severity = Severity.ERROR) -> None:
        results.append(ValidationResult(
            rule_id=rule_id,
            module=self.module_name,
            field=field,
            severity=severity,
            status=Status.FAIL,
            description=desc,
            row_number=row_num,
            actual_value=str(actual),
            expected_value=expected,
        ))

    def _run_validations(self, df: pd.DataFrame) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        col_loan = self._get_col("loan_application_number", df)
        col_num = self._get_col("disbursal_number", df)
        col_disb_amt = self._get_col("disbursal_amount", df)
        col_adj_amt = self._get_col("adjusted_amount", df)
        col_net_amt = self._get_col("net_disbursed_amount", df)
        col_date = self._get_col("payment_date", df)
        col_status = self._get_col("disbursal_status", df)

        seen_keys: Dict[tuple, int] = {}

        for idx, row in df.iterrows():
            row_num = int(idx) + 2

            # DS-001
            loan_val = row.get(col_loan) if col_loan else None
            if is_blank(loan_val):
                self._add(results, "DS-001", "loan_application_number", row_num, "", "Mandatory loan_application_number", "loan_application_number is mandatory")

            # DS-002
            num_val = row.get(col_num) if col_num else None
            num_float = self._to_float(num_val)
            if is_blank(num_val):
                self._add(results, "DS-002", "disbursal_number", row_num, "", "Mandatory disbursal_number", "disbursal_number is mandatory")
            elif num_float is None or num_float < 1:
                self._add(results, "DS-002", "disbursal_number", row_num, num_val, "Positive integer >= 1", "disbursal_number must be integer >= 1")

            # DS-003
            disb_amt_val = row.get(col_disb_amt) if col_disb_amt else None
            disb_float = self._to_float(disb_amt_val)
            if is_blank(disb_amt_val):
                self._add(results, "DS-003", "disbursal_amount", row_num, "", "Mandatory disbursal_amount", "disbursal_amount is mandatory")
            elif disb_float is None or disb_float <= 0:
                self._add(results, "DS-003", "disbursal_amount", row_num, disb_amt_val, "Number > 0", "disbursal_amount must be greater than 0")

            # DS-004
            adj_amt_val = row.get(col_adj_amt) if col_adj_amt else None
            adj_float = 0.0
            if not is_blank(adj_amt_val):
                adj_parsed = self._to_float(adj_amt_val)
                if adj_parsed is None or adj_parsed < 0:
                    self._add(results, "DS-004", "adjusted_amount", row_num, adj_amt_val, "Number >= 0", "adjusted_amount must be >= 0")
                else:
                    adj_float = adj_parsed

            # DS-005 & DS-006
            net_amt_val = row.get(col_net_amt) if col_net_amt else None
            net_float = self._to_float(net_amt_val)
            if is_blank(net_amt_val):
                self._add(results, "DS-005", "net_disbursed_amount", row_num, "", "Mandatory net_disbursed_amount", "net_disbursed_amount is mandatory")
            elif net_float is None or net_float <= 0:
                self._add(results, "DS-005", "net_disbursed_amount", row_num, net_amt_val, "Number > 0", "net_disbursed_amount must be greater than 0")
            elif disb_float is not None:
                expected_net = disb_float - adj_float
                if abs(net_float - expected_net) > 1.0:
                    self._add(results, "DS-006", "net_disbursed_amount", row_num, net_float, f"{expected_net:.2f}", f"net_disbursed_amount ({net_float}) does not match disbursal_amount ({disb_float}) - adjusted_amount ({adj_float})")

            # DS-007
            date_val = row.get(col_date) if col_date else None
            if is_blank(date_val):
                self._add(results, "DS-007", "payment_date", row_num, "", "Valid date string", "payment_date is mandatory")
            elif not self._parse_date(date_val):
                self._add(results, "DS-007", "payment_date", row_num, date_val, "Valid date format (YYYY-MM-DD)", "payment_date has invalid date format")

            # DS-008
            status_val = row.get(col_status) if col_status else None
            if is_blank(status_val):
                self._add(results, "DS-008", "disbursal_status", row_num, "", f"One of: {', '.join(sorted(self.ALLOWED_STATUSES))}", "disbursal_status is mandatory")
            elif str(status_val).strip().lower() not in self.ALLOWED_STATUSES:
                self._add(results, "DS-008", "disbursal_status", row_num, status_val, f"One of: {', '.join(sorted(self.ALLOWED_STATUSES))}", "Invalid disbursal_status")

            # DS-009
            loan_k = str(loan_val).strip() if not is_blank(loan_val) else ""
            num_k = str(num_val).strip() if not is_blank(num_val) else ""
            if loan_k and num_k:
                comp = (loan_k, num_k)
                if comp in seen_keys:
                    self._add(results, "DS-009", "disbursal_number", row_num, num_k, "Unique disbursal_number per loan", f"Duplicate disbursal_number '{num_k}' for loan '{loan_k}', first seen at row {seen_keys[comp]}")
                else:
                    seen_keys[comp] = row_num

        return results


registry.register(DisbursalScheduleValidator)
