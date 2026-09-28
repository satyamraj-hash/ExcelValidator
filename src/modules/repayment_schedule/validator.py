"""
Repayment Schedule Migration Module Validator Implementation.

Implements validation test cases (RPS-001 through RPS-074) specified in the
enterprise migration specification. Integrates cleanly into BaseValidator and
ValidatorRegistry.
"""

import math
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Set
import pandas as pd

from src.core.base import BaseValidator, ValidationRule
from src.core.models import ValidationResult, Severity, Status
from src.core.registry import registry
from src.core.utils import is_blank


class RepaymentScheduleValidator(BaseValidator):
    """
    Production-grade validation engine for Repayment Schedule Excel migration template.

    Validates repayment schedule rows covering:
    1. Mandatory & Loan Identification (RPS-001 - RPS-005)
    2. Installment Amount Calculations (RPS-006 - RPS-009)
    3. Negative Amount Validations (RPS-010 - RPS-016)
    4. Status vs Amount Validation (RPS-017 - RPS-026)
    5. Installment Number Sequence (RPS-027 - RPS-033)
    6. Due Date Validation (RPS-034 - RPS-037)
    7. Opening & Closing Balance Carry Forward (RPS-038 - RPS-042)
    8. Billed Flag Validation (RPS-043 - RPS-046)
    9. TDS Validation (RPS-047 - RPS-049)
    10. Foreclosure (FC) Validations (RPS-050 - RPS-063)
    11. Part Payment (PP) Validations (RPS-064 - RPS-069)
    12. Loan-Level Final Balance (RPS-070 - RPS-074)
    """

    MANDATORY_COLS = [
        "due_date",
        "opening_balance",
        "installment_amount",
        "status",
        "principal",
        "interest",
        "closing_balance",
        "installment_number",
    ]

    COLUMN_ALIASES: Dict[str, List[str]] = {
        "loan_account_no": ["loan_account_no", "loan_account_number", "account_no"],
        "loan_application_number": ["loan_application_number", "application_number", "app_no"],
        "billed_flag": ["billed_flag", "is_billed"],
        "billed_date": ["billed_date"],
        "installment_indicator": ["installment_indicator", "indicator", "schedule_type"],
        "advance_prepay_flag": ["advance_prepay_flag", "advance_flag"],
        "is_advance_repayment": ["is_advance_repayment", "advance_repayment_flag"],
    }

    SPECIAL_INDICATORS = {"FC", "PP", "PEMI", "MP", "MC", "MA", "MN", "M"}

    @property
    def module_name(self) -> str:
        return "Repayment Schedule"

    @property
    def required_columns(self) -> List[str]:
        return self.MANDATORY_COLS

    def _get_matched_col(self, col_key: str, df: pd.DataFrame) -> Optional[str]:
        """Find matching column name in DataFrame, respecting exact match then aliases."""
        df_cols_lower = {str(c).strip().lower(): c for c in df.columns}
        if col_key.lower() in df_cols_lower:
            return df_cols_lower[col_key.lower()]
        aliases = self.COLUMN_ALIASES.get(col_key, [])
        for alias in aliases:
            if alias.lower() in df_cols_lower:
                return df_cols_lower[alias.lower()]
        return None

    def check_missing_columns(self, df: pd.DataFrame) -> List[ValidationResult]:
        """Check for mandatory columns using alias matching."""
        results = []
        for col_key in self.required_columns:
            matched = self._get_matched_col(col_key, df)
            if matched is None:
                results.append(ValidationResult(
                    rule_id="RPS-MANDATORY",
                    module=self.module_name,
                    field=col_key,
                    severity=Severity.ERROR,
                    status=Status.FAIL,
                    description=f"Mandatory column '{col_key}' is completely missing from uploaded file.",
                    row_number=1,
                    actual_value="MISSING",
                    expected_value=f"Column '{col_key}' present"
                ))
        return results

    def get_rules_metadata(self) -> List[ValidationRule]:
        return [
            ValidationRule("RPS-001", "Repayment Schedule", "loan_identification", "Both loan_application_number and loan_account_no blank", Severity.ERROR),
            ValidationRule("RPS-004", "Repayment Schedule", "is_advance_repayment", "advance_prepay_flag required when is_advance_repayment is true/yes", Severity.ERROR),
            ValidationRule("RPS-007", "Repayment Schedule", "installment_amount", "installment_amount must equal principal + interest", Severity.ERROR),
            ValidationRule("RPS-009", "Repayment Schedule", "closing_balance", "closing_balance must equal opening_balance - principal", Severity.ERROR),
            ValidationRule("RPS-010", "Repayment Schedule", "principal", "principal must be non-negative", Severity.ERROR),
            ValidationRule("RPS-011", "Repayment Schedule", "interest", "interest must be non-negative", Severity.ERROR),
            ValidationRule("RPS-012", "Repayment Schedule", "installment_amount", "installment_amount must be non-negative", Severity.ERROR),
            ValidationRule("RPS-013", "Repayment Schedule", "received_amount", "received_amount must be non-negative", Severity.ERROR),
            ValidationRule("RPS-014", "Repayment Schedule", "pending_amount", "pending_amount must be non-negative", Severity.ERROR),
            ValidationRule("RPS-015", "Repayment Schedule", "opening_balance", "opening_balance must be non-negative", Severity.ERROR),
            ValidationRule("RPS-016", "Repayment Schedule", "closing_balance", "closing_balance must be non-negative", Severity.ERROR),
            ValidationRule("RPS-018", "Repayment Schedule", "status", "status=paid requires received_amount = installment_amount", Severity.ERROR),
            ValidationRule("RPS-020", "Repayment Schedule", "status", "status=paid requires pending_amount = 0", Severity.ERROR),
            ValidationRule("RPS-022", "Repayment Schedule", "status", "status=pending requires received_amount = 0", Severity.ERROR),
            ValidationRule("RPS-024", "Repayment Schedule", "status", "status=pending requires pending_amount = installment_amount", Severity.ERROR),
            ValidationRule("RPS-026", "Repayment Schedule", "status", "status=outstanding requires received_amount < installment_amount", Severity.ERROR),
            ValidationRule("RPS-029", "Repayment Schedule", "installment_number", "Normal sequence must start from 0 or 1", Severity.ERROR),
            ValidationRule("RPS-030", "Repayment Schedule", "installment_number", "Missing installment number in sequence", Severity.ERROR),
            ValidationRule("RPS-032", "Repayment Schedule", "installment_number", "Duplicate installment number for same loan", Severity.ERROR),
            ValidationRule("RPS-034", "Repayment Schedule", "due_date", "Duplicate due_date for normal installments in same loan", Severity.ERROR),
            ValidationRule("RPS-036", "Repayment Schedule", "due_date", "Due dates must be in chronological order", Severity.WARNING),
            ValidationRule("RPS-037", "Repayment Schedule", "due_date", "Valid date format YYYY-MM-DD required", Severity.ERROR),
            ValidationRule("RPS-039", "Repayment Schedule", "opening_balance", "opening_balance must equal previous row's closing_balance", Severity.ERROR),
            ValidationRule("RPS-044", "Repayment Schedule", "billed_flag", "billed_flag=true/yes requires non-blank billed_date", Severity.ERROR),
            ValidationRule("RPS-046", "Repayment Schedule", "billed_flag", "billed_flag=false/no requires blank billed_date", Severity.ERROR),
            ValidationRule("RPS-048", "Repayment Schedule", "tds_rate", "tds_rate=0 requires tds_amount=0", Severity.ERROR),
            ValidationRule("RPS-052", "Repayment Schedule", "closing_balance", "FC foreclosure row must have closing_balance = 0", Severity.ERROR),
            ValidationRule("RPS-053", "Repayment Schedule", "status", "No paid/pending/outstanding installment rows allowed after FC row", Severity.ERROR),
            ValidationRule("RPS-058", "Repayment Schedule", "installment_indicator", "FC row must be the final schedule row for the loan", Severity.ERROR),
            ValidationRule("RPS-060", "Repayment Schedule", "installment_indicator", "Multiple FC rows found for same loan", Severity.ERROR),
            ValidationRule("RPS-062", "Repayment Schedule", "status", "Paid installment appears after outstanding installment", Severity.ERROR),
            ValidationRule("RPS-068", "Repayment Schedule", "principal", "Part payment (PP) principal/amount must not be negative", Severity.ERROR),
            ValidationRule("RPS-071", "Repayment Schedule", "closing_balance", "Fully amortized loan final closing_balance should be 0", Severity.WARNING),
            ValidationRule("RPS-072", "Repayment Schedule", "closing_balance", "Final closing balance must not be negative", Severity.ERROR),
        ]

    def _parse_float(self, val: Any) -> Optional[float]:
        """Safely parse float value."""
        if is_blank(val):
            return None
        try:
            f = float(val)
            if math.isnan(f):
                return None
            return f
        except (ValueError, TypeError):
            return None

    def _parse_date(self, val: Any) -> Optional[date]:
        """Safely parse date value."""
        if is_blank(val):
            return None
        if isinstance(val, (pd.Timestamp, datetime)):
            return val.date()
        if isinstance(val, date):
            return val
        val_str = str(val).strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(val_str, fmt).date()
            except ValueError:
                pass
        return None

    def _is_truthy(self, val: Any) -> bool:
        """Check if value is truthy (true, yes, 1)."""
        if is_blank(val):
            return False
        val_str = str(val).strip().lower()
        return val_str in ("true", "yes", "1", "y")

    def _is_falsy(self, val: Any) -> bool:
        """Check if value is falsy (false, no, 0)."""
        if is_blank(val):
            return False
        val_str = str(val).strip().lower()
        return val_str in ("false", "no", "0", "n")

    def _run_validations(self, df: pd.DataFrame) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        def add(rule_id: str, field: str, severity: Severity, description: str,
                row_number: int, actual_value: Any, expected_value: str):
            results.append(ValidationResult(
                rule_id=rule_id,
                module=self.module_name,
                field=field,
                severity=severity,
                status=Status.FAIL,
                description=description,
                row_number=row_number,
                actual_value=str(actual_value) if actual_value is not None else "EMPTY",
                expected_value=expected_value
            ))

        def get_col(name: str) -> Optional[str]:
            return self._get_matched_col(name, df)

        loan_id_col = get_col("loan_id")
        app_no_col = get_col("loan_application_number")
        acct_no_col = get_col("loan_account_no")
        due_date_col = get_col("due_date")
        open_bal_col = get_col("opening_balance")
        inst_amt_col = get_col("installment_amount")
        status_col = get_col("status")
        principal_col = get_col("principal")
        interest_col = get_col("interest")
        close_bal_col = get_col("closing_balance")
        inst_num_col = get_col("installment_number")
        rcvd_amt_col = get_col("received_amount")
        pending_amt_col = get_col("pending_amount")
        is_adv_col = get_col("is_advance_repayment")
        adv_flag_col = get_col("advance_prepay_flag")
        billed_flag_col = get_col("billed_flag")
        billed_date_col = get_col("billed_date")
        tds_rate_col = get_col("tds_rate")
        tds_amt_col = get_col("tds_amount")
        indicator_col = get_col("installment_indicator")

        # Derive effective loan key for grouping
        def get_loan_key(idx: int, row: pd.Series) -> str:
            val_lid = row[loan_id_col] if loan_id_col and loan_id_col in row else None
            val_app = row[app_no_col] if app_no_col and app_no_col in row else None
            val_acc = row[acct_no_col] if acct_no_col and acct_no_col in row else None
            if not is_blank(val_lid):
                return str(val_lid).strip()
            if not is_blank(val_app):
                return str(val_app).strip()
            if not is_blank(val_acc):
                return str(val_acc).strip()
            return f"UNKNOWN_ROW_{idx+2}"

        # ----------------------------------------------------
        # 1. Row-by-Row Validations
        # ----------------------------------------------------
        for idx, row in df.iterrows():
            row_num = idx + 2

            # RPS-001: Both loan_application_number & loan_account_no blank
            val_app = row[app_no_col] if app_no_col else None
            val_acc = row[acct_no_col] if acct_no_col else None
            val_lid = row[loan_id_col] if loan_id_col else None
            if is_blank(val_app) and is_blank(val_acc) and is_blank(val_lid):
                add("RPS-001", "loan_identification", Severity.ERROR,
                    "Both loan_application_number and loan_account_no are blank.",
                    row_num, "EMPTY", "At least one loan identification field provided")

            # RPS-004 / RPS-005: Advance repayment flag
            val_is_adv = row[is_adv_col] if is_adv_col else None
            val_adv_flag = row[adv_flag_col] if adv_flag_col else None
            if self._is_truthy(val_is_adv) and is_blank(val_adv_flag):
                add("RPS-004", "advance_prepay_flag", Severity.ERROR,
                    "advance_prepay_flag is required when is_advance_repayment is true/yes.",
                    row_num, val_is_adv, "Non-blank advance_prepay_flag")

            # Amounts parsing
            prn = self._parse_float(row[principal_col]) if principal_col else None
            intr = self._parse_float(row[interest_col]) if interest_col else None
            inst_amt = self._parse_float(row[inst_amt_col]) if inst_amt_col else None
            open_bal = self._parse_float(row[open_bal_col]) if open_bal_col else None
            close_bal = self._parse_float(row[close_bal_col]) if close_bal_col else None
            rcvd_amt = self._parse_float(row[rcvd_amt_col]) if rcvd_amt_col else None
            pending_amt = self._parse_float(row[pending_amt_col]) if pending_amt_col else None

            # RPS-006 / RPS-007: installment_amount = principal + interest
            if inst_amt is not None and prn is not None and intr is not None:
                expected_inst = prn + intr
                if abs(inst_amt - expected_inst) > 0.05:
                    add("RPS-007", "installment_amount", Severity.ERROR,
                        f"installment_amount ({inst_amt}) does not equal principal ({prn}) + interest ({intr}) = {expected_inst:.2f}.",
                        row_num, inst_amt, f"Expected {expected_inst:.2f}")

            # RPS-008 / RPS-009: closing_balance = opening_balance - principal
            if close_bal is not None and open_bal is not None and prn is not None:
                expected_close = open_bal - prn
                if abs(close_bal - expected_close) > 0.05:
                    add("RPS-009", "closing_balance", Severity.ERROR,
                        f"closing_balance ({close_bal}) does not equal opening_balance ({open_bal}) - principal ({prn}) = {expected_close:.2f}.",
                        row_num, close_bal, f"Expected {expected_close:.2f}")

            # RPS-010 to RPS-016: Negative Amount Checks
            if prn is not None and prn < 0:
                indicator_val = str(row[indicator_col]).strip().upper() if indicator_col and not is_blank(row[indicator_col]) else ""
                if indicator_val == "PP":
                    add("RPS-068", "principal", Severity.ERROR, "Part payment (PP) principal must not be negative.", row_num, prn, "Non-negative amount (>= 0)")
                else:
                    add("RPS-010", "principal", Severity.ERROR, "principal cannot be negative.", row_num, prn, "Non-negative amount (>= 0)")
            if intr is not None and intr < 0:
                add("RPS-011", "interest", Severity.ERROR, "interest cannot be negative.", row_num, intr, "Non-negative amount (>= 0)")
            if inst_amt is not None and inst_amt < 0:
                add("RPS-012", "installment_amount", Severity.ERROR, "installment_amount cannot be negative.", row_num, inst_amt, "Non-negative amount (>= 0)")
            if rcvd_amt is not None and rcvd_amt < 0:
                add("RPS-013", "received_amount", Severity.ERROR, "received_amount cannot be negative.", row_num, rcvd_amt, "Non-negative amount (>= 0)")
            if pending_amt is not None and pending_amt < 0:
                add("RPS-014", "pending_amount", Severity.ERROR, "pending_amount cannot be negative.", row_num, pending_amt, "Non-negative amount (>= 0)")
            if open_bal is not None and open_bal < 0:
                add("RPS-015", "opening_balance", Severity.ERROR, "opening_balance cannot be negative.", row_num, open_bal, "Non-negative amount (>= 0)")
            if close_bal is not None and close_bal < 0:
                add("RPS-016", "closing_balance", Severity.ERROR, "closing_balance cannot be negative.", row_num, close_bal, "Non-negative amount (>= 0)")

            # RPS-017 to RPS-026: Status vs Amount Checks
            if status_col:
                st_val = str(row[status_col]).strip().lower() if not is_blank(row[status_col]) else ""
                if st_val == "paid":
                    if inst_amt is not None and rcvd_amt is not None and abs(rcvd_amt - inst_amt) > 0.05:
                        add("RPS-018", "received_amount", Severity.ERROR,
                            f"status is 'paid' but received_amount ({rcvd_amt}) != installment_amount ({inst_amt}).",
                            row_num, rcvd_amt, f"Expected equal to installment_amount ({inst_amt})")
                    if pending_amt is not None and pending_amt > 0.05:
                        add("RPS-020", "pending_amount", Severity.ERROR,
                            f"status is 'paid' but pending_amount ({pending_amt}) > 0.",
                            row_num, pending_amt, "Expected 0")

                elif st_val == "pending":
                    if rcvd_amt is not None and rcvd_amt > 0.05:
                        add("RPS-022", "received_amount", Severity.ERROR,
                            f"status is 'pending' but received_amount ({rcvd_amt}) > 0.",
                            row_num, rcvd_amt, "Expected 0")
                    if inst_amt is not None and pending_amt is not None and abs(pending_amt - inst_amt) > 0.05:
                        add("RPS-024", "pending_amount", Severity.ERROR,
                            f"status is 'pending' but pending_amount ({pending_amt}) != installment_amount ({inst_amt}).",
                            row_num, pending_amt, f"Expected equal to installment_amount ({inst_amt})")

                elif st_val == "outstanding":
                    if inst_amt is not None and rcvd_amt is not None and rcvd_amt >= inst_amt - 0.05:
                        add("RPS-026", "received_amount", Severity.ERROR,
                            f"status is 'outstanding' but received_amount ({rcvd_amt}) >= installment_amount ({inst_amt}).",
                            row_num, rcvd_amt, f"Expected strictly less than installment_amount ({inst_amt})")

            # RPS-037: Due Date Parsing
            if due_date_col:
                dd_val = row[due_date_col]
                if not is_blank(dd_val):
                    parsed_dd = self._parse_date(dd_val)
                    if parsed_dd is None:
                        add("RPS-037", "due_date", Severity.ERROR,
                            f"due_date '{dd_val}' is invalid or cannot be parsed as YYYY-MM-DD.",
                            row_num, dd_val, "Valid date (e.g. 2024-01-15)")

            # RPS-043 to RPS-046: Billed Flag Validation
            if billed_flag_col:
                bf_val = row[billed_flag_col]
                bd_val = row[billed_date_col] if billed_date_col else None
                if self._is_truthy(bf_val) and is_blank(bd_val):
                    add("RPS-044", "billed_date", Severity.ERROR,
                        "billed_flag is true/yes but billed_date is blank.",
                        row_num, "EMPTY", "Non-blank billed_date")
                elif self._is_falsy(bf_val) and not is_blank(bd_val):
                    add("RPS-046", "billed_date", Severity.ERROR,
                        f"billed_flag is false/no but billed_date '{bd_val}' is provided.",
                        row_num, bd_val, "Blank billed_date")

            # RPS-047 to RPS-049: TDS Validation
            if tds_rate_col:
                tr_val = self._parse_float(row[tds_rate_col])
                ta_val = self._parse_float(row[tds_amt_col]) if tds_amt_col else 0.0
                if tr_val is not None and abs(tr_val) < 0.0001 and ta_val is not None and ta_val > 0.01:
                    add("RPS-048", "tds_amount", Severity.ERROR,
                        f"tds_rate is 0 but tds_amount ({ta_val}) > 0.",
                        row_num, ta_val, "Expected 0")

            # RPS-051 / RPS-052: FC closing_balance check
            if indicator_col:
                ind_val = str(row[indicator_col]).strip().upper() if not is_blank(row[indicator_col]) else ""
                if ind_val == "FC":
                    if close_bal is not None and abs(close_bal) > 0.05:
                        add("RPS-052", "closing_balance", Severity.ERROR,
                            f"Foreclosure (FC) row must have closing_balance = 0 (found {close_bal}).",
                            row_num, close_bal, "Expected 0")

        # ----------------------------------------------------
        # 2. Loan-Level Grouped Validations
        # ----------------------------------------------------
        df_work = df.copy()
        df_work["__row_num"] = [i + 2 for i in range(len(df_work))]
        df_work["__loan_key"] = [get_loan_key(i, row) for i, row in df_work.iterrows()]

        grouped = df_work.groupby("__loan_key", sort=False)

        for loan_key, group in grouped:
            if loan_key.startswith("UNKNOWN_ROW_"):
                continue

            rows_list = group.to_dict("records")
            fc_seen = False
            fc_row_num = None
            saw_outstanding = False

            # Separate normal vs special rows
            normal_rows = []
            special_rows = []

            for r in rows_list:
                ind_val = str(r[indicator_col]).strip().upper() if indicator_col and not is_blank(r[indicator_col]) else ""
                inst_num = self._parse_float(r[inst_num_col]) if inst_num_col else None

                is_special = (ind_val in self.SPECIAL_INDICATORS) or (inst_num is not None and inst_num == 0)

                if is_special:
                    special_rows.append(r)
                else:
                    normal_rows.append(r)

                # Track FC occurrence
                if ind_val == "FC":
                    if fc_seen:
                        add("RPS-060", "installment_indicator", Severity.ERROR,
                            f"Multiple foreclosure (FC) rows found for loan '{loan_key}'.",
                            r["__row_num"], ind_val, "Single FC row per loan")
                    fc_seen = True
                    fc_row_num = r["__row_num"]

                # Check post-FC violations
                elif fc_seen:
                    # RPS-053 / RPS-054 / RPS-055 / RPS-056: Row after FC
                    st_val = str(r[status_col]).strip().lower() if status_col and not is_blank(r[status_col]) else ""
                    add("RPS-053", "installment_indicator", Severity.ERROR,
                        f"Post-foreclosure row found after FC row (Row {fc_row_num}). Status: '{st_val}'.",
                        r["__row_num"], st_val or ind_val or "Normal row", "No rows allowed after foreclosure")

                # RPS-062: Paid after outstanding check
                st_val = str(r[status_col]).strip().lower() if status_col and not is_blank(r[status_col]) else ""
                if st_val == "outstanding":
                    saw_outstanding = True
                elif st_val == "paid" and saw_outstanding and not is_special:
                    add("RPS-062", "status", Severity.ERROR,
                        "Paid installment row appears after an outstanding installment.",
                        r["__row_num"], st_val, "Sequential payment order")

            # ------------------------------------------------
            # Sequence & Carry-Forward on Normal Rows
            # ------------------------------------------------
            if normal_rows:
                # RPS-032: Check duplicate installment numbers
                if inst_num_col:
                    nums = [self._parse_float(r[inst_num_col]) for r in normal_rows if self._parse_float(r[inst_num_col]) is not None]
                    num_counts: Dict[float, int] = {}
                    for n in nums:
                        num_counts[n] = num_counts.get(n, 0) + 1
                    for r in normal_rows:
                        n = self._parse_float(r[inst_num_col])
                        if n is not None and num_counts.get(n, 0) > 1:
                            add("RPS-032", "installment_number", Severity.ERROR,
                                f"Duplicate installment number {int(n)} found for loan '{loan_key}'.",
                                r["__row_num"], int(n), "Unique installment numbers per loan")

                    # Special installment number 0 rows are allowed multiple times.
                    # A PP row and an FC row may both use installment_number=0.
                    # They should only be flagged when their due dates are the same.
                    zero_rows = [
                        r for r in rows_list
                        if self._parse_float(r[inst_num_col]) == 0
                    ]
                    if len(zero_rows) > 1 and due_date_col:
                        zero_date_map: Dict[date, List[Dict[str, Any]]] = {}
                        for r in zero_rows:
                            d_val = self._parse_date(r[due_date_col])
                            if d_val is not None:
                                zero_date_map.setdefault(d_val, []).append(r)

                        for d_val, same_date_rows in zero_date_map.items():
                            if len(same_date_rows) > 1:
                                indicators = [
                                    str(r[indicator_col]).strip().upper()
                                    if indicator_col and not is_blank(r[indicator_col]) else ""
                                    for r in same_date_rows
                                ]
                                add("RPS-067", "due_date", Severity.ERROR,
                                    f"Multiple installment_number=0 special rows found on the same due_date '{d_val}' for loan '{loan_key}'. Indicators: {', '.join(indicators)}.",
                                    same_date_rows[1]["__row_num"], str(d_val),
                                    "Different due_date for multiple zero-installment special rows")

                # RPS-027 to RPS-031: Sequence Start & Gaps
                if inst_num_col:
                    valid_nums_rows = [(self._parse_float(r[inst_num_col]), r["__row_num"]) for r in normal_rows if self._parse_float(r[inst_num_col]) is not None]
                    if valid_nums_rows:
                        sorted_nums = sorted(valid_nums_rows, key=lambda x: x[0])
                        first_num, first_row = sorted_nums[0]

                        # RPS-029: Sequence must start at 0 or 1
                        if first_num not in (0.0, 1.0):
                            add("RPS-029", "installment_number", Severity.ERROR,
                                f"Installment sequence for loan '{loan_key}' starts at {int(first_num)} instead of 0 or 1.",
                                first_row, int(first_num), "Sequence start 0 or 1")

                        # RPS-030 / RPS-031: Missing installment numbers
                        num_set = {int(n) for n, _ in sorted_nums}
                        min_n = int(sorted_nums[0][0])
                        max_n = int(sorted_nums[-1][0])
                        missing = [n for n in range(min_n, max_n + 1) if n not in num_set]
                        if missing:
                            missing_str = ", ".join(map(str, missing[:5])) + ("..." if len(missing) > 5 else "")
                            add("RPS-030", "installment_number", Severity.ERROR,
                                f"Missing installment number(s) in sequence for loan '{loan_key}': {missing_str}.",
                                sorted_nums[0][1], f"Missing: {missing_str}", "Contiguous installment sequence")

                # RPS-034 & RPS-036: Due Date Duplicates & Chronology
                if due_date_col:
                    dates_rows = [(self._parse_date(r[due_date_col]), r["__row_num"]) for r in normal_rows if self._parse_date(r[due_date_col]) is not None]
                    date_counts: Dict[date, int] = {}
                    for d_val, _ in dates_rows:
                        date_counts[d_val] = date_counts.get(d_val, 0) + 1

                    for d_val, r_num in dates_rows:
                        if date_counts.get(d_val, 0) > 1:
                            add("RPS-034", "due_date", Severity.ERROR,
                                f"Duplicate due_date '{d_val}' found for normal installments in loan '{loan_key}'.",
                                r_num, str(d_val), "Unique due_dates for normal installments")

                    # Check chronology
                    prev_date = None
                    for d_val, r_num in dates_rows:
                        if prev_date is not None and d_val < prev_date:
                            add("RPS-036", "due_date", Severity.WARNING,
                                f"due_date '{d_val}' is earlier than previous installment due_date '{prev_date}'.",
                                r_num, str(d_val), f"Chronological date (>= {prev_date})")
                        prev_date = d_val

                # RPS-038 / RPS-039: Opening Balance Carry Forward
                prev_closing = None
                for r in normal_rows:
                    curr_open = self._parse_float(r[open_bal_col]) if open_bal_col else None
                    curr_close = self._parse_float(r[close_bal_col]) if close_bal_col else None

                    if prev_closing is not None and curr_open is not None:
                        if abs(curr_open - prev_closing) > 0.05:
                            add("RPS-039", "opening_balance", Severity.ERROR,
                                f"opening_balance ({curr_open}) does not match previous row's closing_balance ({prev_closing}).",
                                r["__row_num"], curr_open, f"Expected {prev_closing:.2f}")

                    if curr_close is not None:
                        prev_closing = curr_close

            # ------------------------------------------------
            # RPS-070 to RPS-074: Final Balance Checks
            # ------------------------------------------------
            if not fc_seen and normal_rows:
                last_row = normal_rows[-1]
                last_close = self._parse_float(last_row[close_bal_col]) if close_bal_col else None
                if last_close is not None:
                    if last_close > 0.05:
                        add("RPS-071", "closing_balance", Severity.WARNING,
                            f"Final installment for loan '{loan_key}' has non-zero closing_balance ({last_close}).",
                            last_row["__row_num"], last_close, "Expected 0 for fully amortized loan")
                    elif last_close < -0.05:
                        add("RPS-072", "closing_balance", Severity.ERROR,
                            f"Final installment for loan '{loan_key}' has negative closing_balance ({last_close}).",
                            last_row["__row_num"], last_close, "Non-negative balance (>= 0)")

        return results


# Automatic registration on import
registry.register(RepaymentScheduleValidator)
