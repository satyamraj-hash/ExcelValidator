"""
Excess Money Migration Module Validator.
"""
from datetime import datetime, date
import math
from typing import List, Optional, Any, Dict
import pandas as pd

from src.core.base import BaseValidator, ValidationRule
from src.core.models import ValidationResult, Severity, Status
from src.core.registry import registry
from src.core.utils import is_blank


class ExcessMoneyValidator(BaseValidator):
    MANDATORY_COLS = ['loan_application_number', 'receipt_id', 'original_amount', 'paid_amount', 'transaction_date', 'due_date', 'status']

    @property
    def module_name(self) -> str:
        return "Excess Money"

    @property
    def required_columns(self) -> List[str]:
        return self.MANDATORY_COLS

    def get_rules_metadata(self) -> List[ValidationRule]:
        rules = []
        for i, col in enumerate(self.MANDATORY_COLS):
            rules.append(ValidationRule(f"EXCE-{i+1:03d}", self.module_name, col, f"{col} is mandatory", Severity.ERROR))
        return rules

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
        for idx, row in df.iterrows():
            row_num = int(idx) + 2
            for i, col in enumerate(self.MANDATORY_COLS):
                actual_col = self._get_col(col, df)
                val = row.get(actual_col) if actual_col else None
                if is_blank(val):
                    self._add(results, f"EXCE-{i+1:03d}", col, row_num, "", f"Non-blank {col}", f"{col} is mandatory")
        return results

registry.register(ExcessMoneyValidator)
