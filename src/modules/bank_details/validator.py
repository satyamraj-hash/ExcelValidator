"""
Bank Details Migration Module Validator.

Implements BANK-001 through BANK-016 as specified.
"""

import re
from typing import List, Dict, Optional, Any
import pandas as pd

from src.core.base import BaseValidator, ValidationRule
from src.core.models import ValidationResult, Severity, Status
from src.core.registry import registry
from src.core.utils import is_blank


class BankDetailsValidator(BaseValidator):
    """
    Validator for the bank_details migration sheet.

    Covers:
    - Mandatory field checks (BANK-001 to BANK-004)
    - Numeric type checks (BANK-002, BANK-003, BANK-005, BANK-015)
    - IFSC format validation (BANK-006, BANK-007)
    - Name / bank name mandatory (BANK-008, BANK-009)
    - account_type enum (BANK-010)
    - Boolean flag checks (BANK-011, BANK-012, BANK-013)
    - Duplicate composite-key check (BANK-014)
    - Optional field format checks (BANK-015, BANK-016)
    """

    # Allowed values from _lists sheet column bank_account_type
    ALLOWED_ACCOUNT_TYPES = {"savings", "current", "cash_credit", "overdraft"}

    # IFSC: 4 letters + literal '0' + 6 alphanumeric chars
    IFSC_PATTERN = re.compile(r"^[A-Za-z]{4}0[A-Za-z0-9]{6}$")

    MANDATORY_COLS = [
        "loan_application_number",
        "cust_idx",
        "bank_idx",
        "account_number",
        "branch_ifsc",
        "account_holder_name",
        "bank_name",
        "account_type",
        "is_repayment_account",
        "is_disbursal_account",
        "is_default_account",
    ]

    @property
    def module_name(self) -> str:
        return "Bank Details"

    @property
    def required_columns(self) -> List[str]:
        return self.MANDATORY_COLS

    def get_rules_metadata(self) -> List[ValidationRule]:
        return [
            ValidationRule("BANK-001", "Bank Details", "loan_application_number",
                           "loan_application_number is mandatory", Severity.ERROR),
            ValidationRule("BANK-002", "Bank Details", "cust_idx",
                           "cust_idx is mandatory and must be numeric", Severity.ERROR),
            ValidationRule("BANK-003", "Bank Details", "bank_idx",
                           "bank_idx is mandatory and must be numeric", Severity.ERROR),
            ValidationRule("BANK-004", "Bank Details", "account_number",
                           "account_number is mandatory", Severity.ERROR),
            ValidationRule("BANK-005", "Bank Details", "account_number",
                           "account_number must be numeric", Severity.ERROR),
            ValidationRule("BANK-006", "Bank Details", "branch_ifsc",
                           "branch_ifsc is mandatory", Severity.ERROR),
            ValidationRule("BANK-007", "Bank Details", "branch_ifsc",
                           "branch_ifsc must match: 4 letters + 0 + 6 alphanumeric chars", Severity.ERROR),
            ValidationRule("BANK-008", "Bank Details", "account_holder_name",
                           "account_holder_name is mandatory", Severity.ERROR),
            ValidationRule("BANK-009", "Bank Details", "bank_name",
                           "bank_name is mandatory", Severity.ERROR),
            ValidationRule("BANK-010", "Bank Details", "account_type",
                           "account_type must be one of: savings, current, cash_credit, overdraft", Severity.ERROR),
            ValidationRule("BANK-011", "Bank Details", "is_repayment_account",
                           "is_repayment_account must be TRUE or FALSE", Severity.ERROR),
            ValidationRule("BANK-012", "Bank Details", "is_disbursal_account",
                           "is_disbursal_account must be TRUE or FALSE", Severity.ERROR),
            ValidationRule("BANK-013", "Bank Details", "is_default_account",
                           "is_default_account must be TRUE or FALSE", Severity.ERROR),
            ValidationRule("BANK-014", "Bank Details", "loan_application_number+cust_idx+bank_idx",
                           "Composite key (loan_application_number, cust_idx, bank_idx) must be unique", Severity.ERROR),
            ValidationRule("BANK-015", "Bank Details", "micr_code",
                           "micr_code, when populated, must be numeric", Severity.ERROR),
            ValidationRule("BANK-016", "Bank Details", "bank_address",
                           "bank_address, when populated, must not be blank/invalid", Severity.ERROR),
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_col(self, col: str, df: pd.DataFrame) -> Optional[str]:
        """Case-insensitive column lookup."""
        mapping = {str(c).strip().lower(): c for c in df.columns}
        return mapping.get(col.lower())

    def _row_key(self, row_num: int, loan_id: Any) -> str:
        return f"row {row_num} | loan={loan_id}"

    def _is_valid_bool(self, val: Any) -> bool:
        """Return True if val represents a boolean TRUE/FALSE (case-insensitive)."""
        if isinstance(val, bool):
            return True
        if isinstance(val, (int, float)):
            return val in (0, 1)
        if isinstance(val, str):
            return val.strip().lower() in ("true", "false", "1", "0", "yes", "no")
        return False

    def _is_numeric_value(self, val: Any) -> bool:
        """Return True if val (non-blank) is numeric."""
        if is_blank(val):
            return False
        try:
            float(str(val).replace(",", "").strip())
            return True
        except (ValueError, TypeError):
            return False

    def _add(self, results: List[ValidationResult], rule_id: str, field: str,
             row_num: int, actual: Any, expected: str, description: str,
             severity: Severity = Severity.ERROR) -> None:
        results.append(ValidationResult(
            rule_id=rule_id,
            module=self.module_name,
            field=field,
            severity=severity,
            status=Status.FAIL,
            description=description,
            row_number=row_num,
            actual_value=str(actual),
            expected_value=expected,
        ))

    # ------------------------------------------------------------------
    # Main validation
    # ------------------------------------------------------------------

    def _run_validations(self, df: pd.DataFrame) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        # Resolve column names (case-insensitive)
        col_loan = self._get_col("loan_application_number", df)
        col_cust_idx = self._get_col("cust_idx", df)
        col_bank_idx = self._get_col("bank_idx", df)
        col_acct_num = self._get_col("account_number", df)
        col_ifsc = self._get_col("branch_ifsc", df)
        col_holder = self._get_col("account_holder_name", df)
        col_bank_name = self._get_col("bank_name", df)
        col_acct_type = self._get_col("account_type", df)
        col_repay = self._get_col("is_repayment_account", df)
        col_disb = self._get_col("is_disbursal_account", df)
        col_default = self._get_col("is_default_account", df)
        col_micr = self._get_col("micr_code", df)
        col_addr = self._get_col("bank_address", df)

        # BANK-014: duplicate composite key tracking
        seen_keys: Dict[tuple, int] = {}

        for idx, row in df.iterrows():
            row_num = int(idx) + 2  # 1-based + header

            # Determine loan identifier for display
            loan_id = row[col_loan] if col_loan and not is_blank(row.get(col_loan)) else "UNKNOWN"

            # BANK-001: loan_application_number mandatory
            if col_loan and is_blank(row.get(col_loan)):
                self._add(results, "BANK-001", "loan_application_number", row_num,
                          "", "Non-blank loan_application_number",
                          "loan_application_number is mandatory")

            # BANK-002: cust_idx mandatory + numeric
            cust_val = row.get(col_cust_idx) if col_cust_idx else None
            if is_blank(cust_val):
                self._add(results, "BANK-002", "cust_idx", row_num,
                          "", "Non-blank numeric cust_idx",
                          "cust_idx is mandatory")
            elif not self._is_numeric_value(cust_val):
                self._add(results, "BANK-002", "cust_idx", row_num,
                          cust_val, "Numeric value",
                          "cust_idx must be numeric")

            # BANK-003: bank_idx mandatory + numeric
            bank_idx_val = row.get(col_bank_idx) if col_bank_idx else None
            if is_blank(bank_idx_val):
                self._add(results, "BANK-003", "bank_idx", row_num,
                          "", "Non-blank numeric bank_idx",
                          "bank_idx is mandatory")
            elif not self._is_numeric_value(bank_idx_val):
                self._add(results, "BANK-003", "bank_idx", row_num,
                          bank_idx_val, "Numeric value",
                          "bank_idx must be numeric")

            # BANK-004: account_number mandatory
            acct_num_val = row.get(col_acct_num) if col_acct_num else None
            if is_blank(acct_num_val):
                self._add(results, "BANK-004", "account_number", row_num,
                          "", "Non-blank account_number",
                          "account_number is mandatory")
            else:
                # BANK-005: account_number numeric
                if not self._is_numeric_value(acct_num_val):
                    self._add(results, "BANK-005", "account_number", row_num,
                              acct_num_val, "Numeric value",
                              "account_number must be numeric")

            # BANK-006 + BANK-007: branch_ifsc
            ifsc_val = row.get(col_ifsc) if col_ifsc else None
            if is_blank(ifsc_val):
                self._add(results, "BANK-006", "branch_ifsc", row_num,
                          "", "Non-blank branch_ifsc",
                          "branch_ifsc is mandatory")
            else:
                ifsc_str = str(ifsc_val).strip()
                if not self.IFSC_PATTERN.match(ifsc_str):
                    self._add(results, "BANK-007", "branch_ifsc", row_num,
                              ifsc_str,
                              "4 letters + '0' + 6 alphanumeric (e.g. SBIN0004306)",
                              "branch_ifsc format invalid")

            # BANK-008: account_holder_name mandatory
            if col_holder and is_blank(row.get(col_holder)):
                self._add(results, "BANK-008", "account_holder_name", row_num,
                          "", "Non-blank account_holder_name",
                          "account_holder_name is mandatory")

            # BANK-009: bank_name mandatory
            if col_bank_name and is_blank(row.get(col_bank_name)):
                self._add(results, "BANK-009", "bank_name", row_num,
                          "", "Non-blank bank_name",
                          "bank_name is mandatory")

            # BANK-010: account_type enum
            acct_type_val = row.get(col_acct_type) if col_acct_type else None
            if not is_blank(acct_type_val):
                if str(acct_type_val).strip().lower() not in self.ALLOWED_ACCOUNT_TYPES:
                    self._add(results, "BANK-010", "account_type", row_num,
                              acct_type_val,
                              f"One of: {', '.join(sorted(self.ALLOWED_ACCOUNT_TYPES))}",
                              "account_type has invalid value")
            else:
                # mandatory – it's in required_columns but let's flag explicitly
                self._add(results, "BANK-010", "account_type", row_num,
                          "", f"One of: {', '.join(sorted(self.ALLOWED_ACCOUNT_TYPES))}",
                          "account_type is mandatory")

            # BANK-011: is_repayment_account boolean
            repay_val = row.get(col_repay) if col_repay else None
            if not is_blank(repay_val) and not self._is_valid_bool(repay_val):
                self._add(results, "BANK-011", "is_repayment_account", row_num,
                          repay_val, "TRUE or FALSE",
                          "is_repayment_account must be TRUE or FALSE")

            # BANK-012: is_disbursal_account boolean
            disb_val = row.get(col_disb) if col_disb else None
            if not is_blank(disb_val) and not self._is_valid_bool(disb_val):
                self._add(results, "BANK-012", "is_disbursal_account", row_num,
                          disb_val, "TRUE or FALSE",
                          "is_disbursal_account must be TRUE or FALSE")

            # BANK-013: is_default_account boolean
            default_val = row.get(col_default) if col_default else None
            if not is_blank(default_val) and not self._is_valid_bool(default_val):
                self._add(results, "BANK-013", "is_default_account", row_num,
                          default_val, "TRUE or FALSE",
                          "is_default_account must be TRUE or FALSE")

            # BANK-014: composite key duplicate check
            loan_key = str(row.get(col_loan, "")).strip() if col_loan else ""
            cust_key = str(cust_val).strip() if not is_blank(cust_val) else ""
            bidx_key = str(bank_idx_val).strip() if not is_blank(bank_idx_val) else ""
            composite = (loan_key, cust_key, bidx_key)
            if composite in seen_keys:
                self._add(results, "BANK-014",
                          "loan_application_number+cust_idx+bank_idx", row_num,
                          f"{loan_key}|{cust_key}|{bidx_key}",
                          "Unique composite key",
                          f"Duplicate composite key — first seen at row {seen_keys[composite]}")
            else:
                seen_keys[composite] = row_num

            # BANK-015: micr_code — when populated, must be numeric
            if col_micr:
                micr_val = row.get(col_micr)
                if not is_blank(micr_val) and not self._is_numeric_value(micr_val):
                    self._add(results, "BANK-015", "micr_code", row_num,
                              micr_val, "Numeric value",
                              "micr_code must be numeric when provided")

            # BANK-016: bank_address — when populated, must not be blank/whitespace-only
            if col_addr:
                addr_val = row.get(col_addr)
                addr_is_null = pd.isna(addr_val) if not isinstance(addr_val, (list, dict)) else False
                if not addr_is_null and addr_val is not None:
                    if str(addr_val).strip() == "":
                        self._add(results, "BANK-016", "bank_address", row_num,
                                  repr(addr_val), "Non-empty string",
                                  "bank_address must not be blank/whitespace-only when provided")

        return results


registry.register(BankDetailsValidator)
