"""
Abstract Base Class and Interfaces for Migration Module Validators.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Set
import pandas as pd

from src.core.models import Severity, Status, ValidationResult


@dataclass
class ValidationRule:
    """Metadata describing an individual validation rule."""
    rule_id: str
    module: str
    field: str
    description: str
    severity: Severity


class BaseValidator(ABC):
    """
    Abstract base class for all Excel migration module validators.
    
    Subclasses (e.g. CustomerValidator, LoanValidator) must implement:
    - module_name property
    - required_columns property
    - get_rules_metadata() method
    - _run_validations(df: pd.DataFrame) -> List[ValidationResult]
    """

    @property
    @abstractmethod
    def module_name(self) -> str:
        """Return the unique human-readable module name (e.g. 'Customer')."""
        pass

    @property
    @abstractmethod
    def required_columns(self) -> List[str]:
        """Return the list of mandatory column headers expected in the Excel sheet."""
        pass

    @abstractmethod
    def get_rules_metadata(self) -> List[ValidationRule]:
        """Return metadata for all validation rules defined in this validator module."""
        pass

    @abstractmethod
    def _run_validations(self, df: pd.DataFrame) -> List[ValidationResult]:
        """Module-specific business rule validation logic."""
        pass

    def check_missing_columns(self, df: pd.DataFrame) -> List[ValidationResult]:
        """
        Structural check: Verifies that all required columns are present in the Excel file.
        Returns a FAIL result for each missing column.
        """
        results = []
        df_cols_set = {str(c).strip().lower() for c in df.columns}
        
        for req_col in self.required_columns:
            if str(req_col).strip().lower() not in df_cols_set:
                results.append(
                    ValidationResult(
                        rule_id=f"{self.module_name.upper()[:4]}_STRUCT_001",
                        module=self.module_name,
                        field=req_col,
                        severity=Severity.ERROR,
                        status=Status.FAIL,
                        description=f"Missing mandatory column '{req_col}' in uploaded file.",
                        row_number=None,
                        actual_value="COLUMN_MISSING",
                        expected_value=req_col
                    )
                )
        return results

    def validate(self, df: pd.DataFrame) -> List[ValidationResult]:
        """
        Main entry point to execute validation on a given DataFrame.
        
        Workflow:
        1. Perform structural missing column checks.
        2. If mandatory columns are missing, return structural errors immediately or continue.
        3. Execute module-specific validation rules.
        """
        results: List[ValidationResult] = []

        # 1. Structural column check
        missing_col_results = self.check_missing_columns(df)
        results.extend(missing_col_results)

        # 2. Run module validations (even if columns missing, run remaining where possible)
        try:
            module_results = self._run_validations(df)
            results.extend(module_results)
        except Exception as exc:
            results.append(
                ValidationResult(
                    rule_id=f"{self.module_name.upper()[:4]}_ERR_999",
                    module=self.module_name,
                    field="SYSTEM",
                    severity=Severity.ERROR,
                    status=Status.FAIL,
                    description=f"Unexpected error during validation execution: {str(exc)}",
                    row_number=None,
                    actual_value=type(exc).__name__,
                    expected_value="Clean execution"
                )
            )

        return results
