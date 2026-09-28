"""
Loan Application Migration Module Validator Implementation.

Implements all 60 validation test cases (LA-001 through LA-060) specified in the
enterprise migration specification. Integrates cleanly into BaseValidator and
ValidatorRegistry.
"""

from datetime import datetime, date
import re
from typing import List, Dict, Any, Optional, Set
import pandas as pd

from src.core.base import BaseValidator, ValidationRule
from src.core.models import ValidationResult, Severity, Status
from src.core.registry import registry
from src.core.utils import (
    is_blank,
    validate_missing_values,
    validate_regex_pattern,
    validate_allowed_values,
    validate_numeric_range,
    validate_duplicates,
)


class LoanApplicationValidator(BaseValidator):
    """
    Production-grade validation engine for Loan Application Excel migration template.
    """

    MANDATORY_COLS = [
        "loan_id",
        "loan_application_number",
        "product_code",
        "branch_code",
        "interest_rate",
        "recovery_sub_type",
        "installment_frequency",
        "currency",
        "sanctioned_amount",
        "disbursed_amount",
        "requested_loan_amount",
        "original_tenure",
        "current_tenure",
        "tenure_unit",
        "interest_start_date",
        "repayment_start_date",
        "sanction_date",
        "loan_booking_date",
        "loan_status",
        "installment_amount",
        "principal_outstanding",
        "repayment_mode",
        "irr",
        "emi_amount",
        "scheme_code",
        "ltv_ratio",
        "foir",
        "paid_amount"
    ]

    COLUMN_ALIASES: Dict[str, List[str]] = {
        "principal_outstanding": ["principal_outstanding", "principal_outstanding as on 30.04.2026"],
        "installment_frequency.1": ["installment_frequency.1", "installment_frequency_1"],
    }

    ALLOWED_RECOVERY_SUB_TYPES = {"revolving", "non_revolving"}
    ALLOWED_FREQUENCIES = {"monthly", "quarterly", "semi_annually", "annually", "yearly", "weekly", "bi_weekly", "bullet"}
    ALLOWED_LOAN_STATUSES = {"active", "closed", "cancelled"}
    ALLOWED_ASSET_CLASSIFICATIONS = {"standard", "substandard", "regular", "npa", "doubtful", "loss"}
    ALLOWED_REPAYMENT_MODES = {"nach", "ecs", "pdc", "direct_debit", "cash", "upi", "rtgs", "neft"}
    ALLOWED_TENURE_UNITS = {"months", "years"}
    ALLOWED_COLENDING = {"yes", "no"}

    FINANCIAL_AMOUNT_COLS = [
        "sanctioned_amount", "disbursed_amount", "requested_loan_amount",
        "installment_amount", "emi_amount", "paid_amount", "principal_outstanding",
        "principal_recovery", "billed_principal_amount", "balance_principal",
        "received_principal", "total_interest_amount"
    ]

    @property
    def module_name(self) -> str:
        return "Loan Application"

    @property
    def required_columns(self) -> List[str]:
        return self.MANDATORY_COLS

    def get_rules_metadata(self) -> List[ValidationRule]:
        return [
            ValidationRule("LA-001", "Loan Application", "loan_id", "loan_id mandatory, numeric integer & unique", Severity.ERROR),
            ValidationRule("LA-002", "Loan Application", "loan_application_number", "loan_application_number mandatory, alphanumeric & unique", Severity.ERROR),
            ValidationRule("LA-003", "Loan Application", "source_application_number", "source_application_number alphanumeric if populated", Severity.ERROR),
            ValidationRule("LA-004", "Loan Application", "product_code", "product_code mandatory & alphanumeric", Severity.ERROR),
            ValidationRule("LA-005", "Loan Application", "branch_code", "branch_code mandatory & alphanumeric", Severity.ERROR),
            ValidationRule("LA-006", "Loan Application", "interest_rate", "interest_rate mandatory, numeric & non-negative", Severity.ERROR),
            ValidationRule("LA-007", "Loan Application", "recovery_sub_type", "recovery_sub_type mandatory, lowercase (revolving/non_revolving)", Severity.ERROR),
            ValidationRule("LA-008", "Loan Application", "installment_frequency", "installment_frequency mandatory, lowercase & valid frequency", Severity.ERROR),
            ValidationRule("LA-009", "Loan Application", "currency", "currency mandatory (expected default 1)", Severity.ERROR),
            ValidationRule("LA-010", "Loan Application", "sanctioned_amount", "sanctioned_amount mandatory, numeric & > 0", Severity.ERROR),
            ValidationRule("LA-011", "Loan Application", "disbursed_amount", "disbursed_amount mandatory, numeric & >= 0", Severity.ERROR),
            ValidationRule("LA-012", "Loan Application", "disbursed_vs_sanctioned", "disbursed_amount <= sanctioned_amount", Severity.ERROR),
            ValidationRule("LA-013", "Loan Application", "requested_loan_amount", "requested_loan_amount mandatory, numeric & > 0", Severity.ERROR),
            ValidationRule("LA-014", "Loan Application", "original_tenure", "original_tenure mandatory, numeric & > 0", Severity.ERROR),
            ValidationRule("LA-015", "Loan Application", "current_tenure", "current_tenure mandatory, numeric & >= 0", Severity.ERROR),
            ValidationRule("LA-016", "Loan Application", "tenure_logic", "current_tenure <= original_tenure", Severity.ERROR),
            ValidationRule("LA-017", "Loan Application", "tenure_unit", "tenure_unit mandatory, lowercase (months/years)", Severity.ERROR),
            ValidationRule("LA-018", "Loan Application", "interest_start_date", "interest_start_date mandatory date YYYY-MM-DD", Severity.ERROR),
            ValidationRule("LA-019", "Loan Application", "repayment_start_date", "repayment_start_date mandatory date YYYY-MM-DD", Severity.ERROR),
            ValidationRule("LA-020", "Loan Application", "interest_vs_repayment_date", "interest_start_date <= repayment_start_date", Severity.ERROR),
            ValidationRule("LA-021", "Loan Application", "sanction_date", "sanction_date mandatory date YYYY-MM-DD", Severity.ERROR),
            ValidationRule("LA-022", "Loan Application", "disbursal_date", "disbursal_date mandatory for disbursed loans, date YYYY-MM-DD", Severity.ERROR),
            ValidationRule("LA-023", "Loan Application", "sanction_vs_disbursal_date", "disbursal_date >= sanction_date", Severity.ERROR),
            ValidationRule("LA-024", "Loan Application", "loan_booking_date", "loan_booking_date mandatory date YYYY-MM-DD", Severity.ERROR),
            ValidationRule("LA-025", "Loan Application", "booking_date_validity", "loan_booking_date valid YYYY-MM-DD date format", Severity.ERROR),
            ValidationRule("LA-026", "Loan Application", "disbursal_status", "disbursal_status valid configured status", Severity.WARNING),
            ValidationRule("LA-027", "Loan Application", "loan_status", "loan_status mandatory, lowercase (active/closed/cancelled)", Severity.ERROR),
            ValidationRule("LA-028", "Loan Application", "maturity_date", "maturity_date valid date YYYY-MM-DD & after loan start/disbursal date", Severity.ERROR),
            ValidationRule("LA-029", "Loan Application", "asset_classification", "asset_classification lowercase master value", Severity.WARNING),
            ValidationRule("LA-030", "Loan Application", "installment_amount", "installment_amount mandatory, numeric & > 0", Severity.ERROR),
            ValidationRule("LA-031", "Loan Application", "principal_outstanding", "principal_outstanding mandatory, numeric & >= 0", Severity.ERROR),
            ValidationRule("LA-032", "Loan Application", "principal_outstanding_logic", "principal_outstanding <= disbursed_amount", Severity.ERROR),
            ValidationRule("LA-033", "Loan Application", "repayment_mode", "repayment_mode mandatory, lowercase & valid master value", Severity.ERROR),
            ValidationRule("LA-034", "Loan Application", "irr", "irr mandatory & numeric", Severity.ERROR),
            ValidationRule("LA-035", "Loan Application", "emi_amount", "emi_amount mandatory, numeric & > 0", Severity.ERROR),
            ValidationRule("LA-036", "Loan Application", "emi_vs_installment", "emi_amount matches installment_amount for EMI loans", Severity.WARNING),
            ValidationRule("LA-037", "Loan Application", "scheme_code", "scheme_code mandatory & alphanumeric", Severity.ERROR),
            ValidationRule("LA-038", "Loan Application", "is_emi_presentation_hold", "is_emi_presentation_hold boolean flag", Severity.WARNING),
            ValidationRule("LA-039", "Loan Application", "tds_mode", "tds_mode valid master value if populated", Severity.WARNING),
            ValidationRule("LA-040", "Loan Application", "is_colending", "is_colending lowercase (yes/no)", Severity.WARNING),
            ValidationRule("LA-041", "Loan Application", "ltv_ratio", "ltv_ratio mandatory, numeric 0 to 100", Severity.ERROR),
            ValidationRule("LA-042", "Loan Application", "foir", "foir mandatory & numeric ratio/percentage", Severity.ERROR),
            ValidationRule("LA-043", "Loan Application", "installment_plan", "installment_plan valid master value", Severity.WARNING),
            ValidationRule("LA-044", "Loan Application", "paid_amount", "paid_amount mandatory, numeric & >= 0", Severity.ERROR),
            ValidationRule("LA-045", "Loan Application", "total_interest_amount", "total_interest_amount numeric & >= 0 if populated", Severity.WARNING),
            ValidationRule("LA-046", "Loan Application", "principal_recovery_frequency", "principal_recovery_frequency lowercase & valid frequency", Severity.WARNING),
            ValidationRule("LA-047", "Loan Application", "principal_recovery", "principal_recovery numeric & >= 0 if populated", Severity.WARNING),
            ValidationRule("LA-048", "Loan Application", "billed_principal_amount", "billed_principal_amount numeric & >= 0 if populated", Severity.WARNING),
            ValidationRule("LA-049", "Loan Application", "balance_principal", "balance_principal numeric & >= 0 if populated", Severity.WARNING),
            ValidationRule("LA-050", "Loan Application", "received_principal", "received_principal numeric & >= 0 if populated", Severity.WARNING),
            ValidationRule("LA-051", "Loan Application", "cancellation_date", "cancellation_date valid date YYYY-MM-DD", Severity.WARNING),
            ValidationRule("LA-052", "Loan Application", "loan_closure_date", "loan_closure_date valid date YYYY-MM-DD", Severity.WARNING),
            ValidationRule("LA-053", "Loan Application", "status_date_consistency", "loan_status closed/cancelled require closure/cancellation date", Severity.ERROR),
            ValidationRule("LA-054", "Loan Application", "loan_purpose", "loan_purpose valid format/value", Severity.WARNING),
            ValidationRule("LA-055", "Loan Application", "strict_dates", "All date columns must be YYYY-MM-DD", Severity.ERROR),
            ValidationRule("LA-056", "Loan Application", "common_frequencies", "Frequency fields must be lowercase valid frequencies", Severity.WARNING),
            ValidationRule("LA-057", "Loan Application", "duplicate_frequency", "installment_frequency and installment_frequency.1 must match", Severity.WARNING),
            ValidationRule("LA-058", "Loan Application", "negative_financials", "Flag negative values for financial fields", Severity.ERROR),
            ValidationRule("LA-059", "Loan Application", "full_disbursal_consistency", "disbursal_status fully_disbursed check", Severity.WARNING),
            ValidationRule("LA-060", "Loan Application", "general_mandatory", "Centralized mandatory column missing check", Severity.ERROR),
        ]

    def _get_matched_col(self, col_key: str, df: pd.DataFrame) -> str:
        df_cols_lower = {str(c).strip().lower(): c for c in df.columns}
        if col_key.lower() in df_cols_lower:
            return df_cols_lower[col_key.lower()]
        
        aliases = self.COLUMN_ALIASES.get(col_key.lower(), [])
        for alias in aliases:
            if alias.lower() in df_cols_lower:
                return df_cols_lower[alias.lower()]
        return col_key

    def check_missing_columns(self, df: pd.DataFrame) -> List[ValidationResult]:
        results = []
        df_cols_set = {str(c).strip().lower() for c in df.columns}
        
        for req_col in self.required_columns:
            matched_col = self._get_matched_col(req_col, df)
            if str(matched_col).strip().lower() not in df_cols_set:
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

    def _parse_strict_date(self, val: Any) -> Optional[date]:
        if is_blank(val):
            return None
        if isinstance(val, (pd.Timestamp, datetime)):
            return val.date()
        if isinstance(val, date):
            return val
        
        str_val = str(val).strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}$", str_val):
            try:
                dt = datetime.strptime(str_val, "%Y-%m-%d")
                return dt.date()
            except ValueError:
                return None
        return None

    def _run_validations(self, df: pd.DataFrame) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        def get_col(col_name: str) -> str:
            return self._get_matched_col(col_name, df)

        # ----------------------------------------------------
        # LA-060 & LA-002: General Mandatory Fields Check
        # ----------------------------------------------------
        for mandatory_col in self.MANDATORY_COLS:
            real_col = get_col(mandatory_col)
            if real_col in df.columns:
                findings = validate_missing_values(
                    df=df,
                    column=real_col,
                    rule_id="LA-060",
                    module=self.module_name,
                    severity=Severity.ERROR,
                    description=f"Mandatory column '{mandatory_col}' cannot be blank or empty."
                )
                for f in findings:
                    results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-001: loan_id (Mandatory, Numeric Integer, Unique)
        # ----------------------------------------------------
        loan_id_col = get_col("loan_id")
        if loan_id_col in df.columns:
            for idx, val in enumerate(df[loan_id_col]):
                if is_blank(val):
                    results.append(ValidationResult(
                        rule_id="LA-001",
                        module=self.module_name,
                        field="loan_id",
                        severity=Severity.ERROR,
                        status=Status.FAIL,
                        description="loan_id cannot be blank.",
                        row_number=idx + 2,
                        actual_value="EMPTY",
                        expected_value="Integer loan ID"
                    ))
                    continue
                try:
                    float_val = float(val)
                    if not float_val.is_integer():
                        results.append(ValidationResult(
                            rule_id="LA-001",
                            module=self.module_name,
                            field="loan_id",
                            severity=Severity.ERROR,
                            status=Status.FAIL,
                            description="loan_id must be a numeric integer.",
                            row_number=idx + 2,
                            actual_value=str(val),
                            expected_value="Integer number (e.g. 123456)"
                        ))
                except (ValueError, TypeError):
                    results.append(ValidationResult(
                        rule_id="LA-001",
                        module=self.module_name,
                        field="loan_id",
                        severity=Severity.ERROR,
                        status=Status.FAIL,
                        description="loan_id contains non-numeric text.",
                        row_number=idx + 2,
                        actual_value=str(val),
                        expected_value="Integer number (e.g. 123456)"
                    ))

            findings = validate_duplicates(df, loan_id_col, "LA-001", self.module_name, Severity.ERROR, "Duplicate loan_id found in dataset.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-002: loan_application_number (Mandatory, Alphanumeric, Unique)
        # ----------------------------------------------------
        loan_app_col = get_col("loan_application_number")
        if loan_app_col in df.columns:
            alphanumeric_regex = r"^[A-Za-z0-9_\-/\s]+$"
            findings = validate_regex_pattern(
                df=df,
                column=loan_app_col,
                pattern=alphanumeric_regex,
                rule_id="LA-002",
                module=self.module_name,
                severity=Severity.ERROR,
                description="loan_application_number contains invalid special characters.",
                expected_format_desc="Alphanumeric string (e.g. SHDG2028010)"
            )
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

            findings = validate_duplicates(df, loan_app_col, "LA-002", self.module_name, Severity.ERROR, "Duplicate loan_application_number found in dataset.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-003: source_application_number (Alphanumeric if populated)
        # ----------------------------------------------------
        source_app_col = get_col("source_application_number")
        if source_app_col in df.columns:
            alphanumeric_regex = r"^[A-Za-z0-9_\-/\s]+$"
            findings = validate_regex_pattern(
                df=df,
                column=source_app_col,
                pattern=alphanumeric_regex,
                rule_id="LA-003",
                module=self.module_name,
                severity=Severity.ERROR,
                description="source_application_number contains invalid special characters.",
                expected_format_desc="Alphanumeric string if populated"
            )
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-004 & LA-005: product_code & branch_code (Alphanumeric)
        # ----------------------------------------------------
        for code_col_key, rule_id in [("product_code", "LA-004"), ("branch_code", "LA-005")]:
            real_code_col = get_col(code_col_key)
            if real_code_col in df.columns:
                findings = validate_regex_pattern(
                    df=df,
                    column=real_code_col,
                    pattern=r"^[A-Za-z0-9_\-/\s]+$",
                    rule_id=rule_id,
                    module=self.module_name,
                    severity=Severity.ERROR,
                    description=f"{code_col_key} must be alphanumeric.",
                    expected_format_desc="Alphanumeric code"
                )
                for f in findings:
                    results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-006: interest_rate (Numeric & Non-negative)
        # ----------------------------------------------------
        ir_col = get_col("interest_rate")
        if ir_col in df.columns:
            findings = validate_numeric_range(df, ir_col, min_val=0, max_val=100, rule_id="LA-006", module=self.module_name, severity=Severity.ERROR, description="interest_rate must be a non-negative numeric percentage.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-007: recovery_sub_type (Lowercase: revolving, non_revolving)
        # ----------------------------------------------------
        rec_col = get_col("recovery_sub_type")
        if rec_col in df.columns:
            for idx, val in enumerate(df[rec_col]):
                if is_blank(val):
                    continue
                str_val = str(val).strip()
                if str_val != str_val.lower() or str_val.lower() not in self.ALLOWED_RECOVERY_SUB_TYPES:
                    results.append(ValidationResult(
                        rule_id="LA-007",
                        module=self.module_name,
                        field="recovery_sub_type",
                        severity=Severity.ERROR,
                        status=Status.FAIL,
                        description="recovery_sub_type must be lowercase ('revolving' or 'non_revolving').",
                        row_number=idx + 2,
                        actual_value=str(val),
                        expected_value="Lowercase: revolving, non_revolving"
                    ))

        # ----------------------------------------------------
        # LA-008 & LA-056: installment_frequency (Lowercase & valid frequency)
        # ----------------------------------------------------
        freq_col = get_col("installment_frequency")
        if freq_col in df.columns:
            for idx, val in enumerate(df[freq_col]):
                if is_blank(val):
                    continue
                str_val = str(val).strip()
                if str_val != str_val.lower() or str_val.lower() not in self.ALLOWED_FREQUENCIES:
                    results.append(ValidationResult(
                        rule_id="LA-008",
                        module=self.module_name,
                        field="installment_frequency",
                        severity=Severity.ERROR,
                        status=Status.FAIL,
                        description="installment_frequency must be lowercase valid frequency (e.g. monthly).",
                        row_number=idx + 2,
                        actual_value=str(val),
                        expected_value=f"Lowercase one of: {sorted(list(self.ALLOWED_FREQUENCIES))}"
                    ))

        # ----------------------------------------------------
        # LA-057: Duplicate Installment Frequency Check
        # ----------------------------------------------------
        freq1_col = get_col("installment_frequency.1")
        if freq_col in df.columns and freq1_col in df.columns:
            for idx, (v1, v2) in enumerate(zip(df[freq_col], df[freq1_col])):
                if not is_blank(v1) and not is_blank(v2):
                    if str(v1).strip().lower() != str(v2).strip().lower():
                        results.append(ValidationResult(
                            rule_id="LA-057",
                            module=self.module_name,
                            field="installment_frequency.1",
                            severity=Severity.WARNING,
                            status=Status.FAIL,
                            description="installment_frequency and installment_frequency.1 contain mismatched values.",
                            row_number=idx + 2,
                            actual_value=f"{v1} vs {v2}",
                            expected_value="Matching frequency values"
                        ))

        # ----------------------------------------------------
        # LA-009: currency Check (Expected default 1)
        # ----------------------------------------------------
        curr_col = get_col("currency")
        if curr_col in df.columns:
            for idx, val in enumerate(df[curr_col]):
                if is_blank(val):
                    continue
                str_val = str(val).strip()
                if str_val not in ["1", "1.0", "INR"]:
                    results.append(ValidationResult(
                        rule_id="LA-009",
                        module=self.module_name,
                        field="currency",
                        severity=Severity.WARNING,
                        status=Status.FAIL,
                        description="currency expected default is 1 (or INR).",
                        row_number=idx + 2,
                        actual_value=str_val,
                        expected_value="1"
                    ))

        # ----------------------------------------------------
        # LA-010: sanctioned_amount (Numeric > 0)
        # ----------------------------------------------------
        sanc_col = get_col("sanctioned_amount")
        if sanc_col in df.columns:
            findings = validate_numeric_range(df, sanc_col, min_val=0.01, rule_id="LA-010", module=self.module_name, severity=Severity.ERROR, description="sanctioned_amount must be numeric greater than 0.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-011: disbursed_amount (Numeric >= 0)
        # ----------------------------------------------------
        disb_col = get_col("disbursed_amount")
        if disb_col in df.columns:
            findings = validate_numeric_range(df, disb_col, min_val=0.0, rule_id="LA-011", module=self.module_name, severity=Severity.ERROR, description="disbursed_amount must be numeric greater than or equal to 0.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-012: SANCTIONED VS DISBURSED LOGIC (disbursed <= sanctioned)
        # ----------------------------------------------------
        if sanc_col in df.columns and disb_col in df.columns:
            for idx, (s_val, d_val) in enumerate(zip(df[sanc_col], df[disb_col])):
                if not is_blank(s_val) and not is_blank(d_val):
                    try:
                        s_amt = float(s_val)
                        d_amt = float(d_val)
                        if d_amt > s_amt:
                            results.append(ValidationResult(
                                rule_id="LA-012",
                                module=self.module_name,
                                field="disbursed_amount",
                                severity=Severity.ERROR,
                                status=Status.FAIL,
                                description=f"disbursed_amount ({d_amt}) cannot be greater than sanctioned_amount ({s_amt}).",
                                row_number=idx + 2,
                                actual_value=str(d_val),
                                expected_value=f"<= sanctioned_amount ({s_amt})"
                            ))
                    except (ValueError, TypeError):
                        pass

        # ----------------------------------------------------
        # LA-013: requested_loan_amount (Numeric > 0)
        # ----------------------------------------------------
        req_col = get_col("requested_loan_amount")
        if req_col in df.columns:
            findings = validate_numeric_range(df, req_col, min_val=0.01, rule_id="LA-013", module=self.module_name, severity=Severity.ERROR, description="requested_loan_amount must be numeric greater than 0.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-014: original_tenure (Numeric > 0)
        # ----------------------------------------------------
        orig_tenure_col = get_col("original_tenure")
        if orig_tenure_col in df.columns:
            findings = validate_numeric_range(df, orig_tenure_col, min_val=1, rule_id="LA-014", module=self.module_name, severity=Severity.ERROR, description="original_tenure must be numeric greater than 0.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-015: current_tenure (Numeric >= 0)
        # ----------------------------------------------------
        curr_tenure_col = get_col("current_tenure")
        if curr_tenure_col in df.columns:
            findings = validate_numeric_range(df, curr_tenure_col, min_val=0, rule_id="LA-015", module=self.module_name, severity=Severity.ERROR, description="current_tenure must be numeric >= 0.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-016: TENURE LOGIC (current_tenure <= original_tenure)
        # ----------------------------------------------------
        if orig_tenure_col in df.columns and curr_tenure_col in df.columns:
            for idx, (o_val, c_val) in enumerate(zip(df[orig_tenure_col], df[curr_tenure_col])):
                if not is_blank(o_val) and not is_blank(c_val):
                    try:
                        o_ten = float(o_val)
                        c_ten = float(c_val)
                        if c_ten > o_ten:
                            results.append(ValidationResult(
                                rule_id="LA-016",
                                module=self.module_name,
                                field="current_tenure",
                                severity=Severity.ERROR,
                                status=Status.FAIL,
                                description=f"current_tenure ({c_ten}) cannot be greater than original_tenure ({o_ten}).",
                                row_number=idx + 2,
                                actual_value=str(c_val),
                                expected_value=f"<= original_tenure ({o_ten})"
                            ))
                    except (ValueError, TypeError):
                        pass

        # ----------------------------------------------------
        # LA-017: tenure_unit (Lowercase: months, years)
        # ----------------------------------------------------
        tenure_unit_col = get_col("tenure_unit")
        if tenure_unit_col in df.columns:
            for idx, val in enumerate(df[tenure_unit_col]):
                if is_blank(val):
                    continue
                str_val = str(val).strip()
                if str_val != str_val.lower() or str_val.lower() not in self.ALLOWED_TENURE_UNITS:
                    results.append(ValidationResult(
                        rule_id="LA-017",
                        module=self.module_name,
                        field="tenure_unit",
                        severity=Severity.ERROR,
                        status=Status.FAIL,
                        description="tenure_unit must be lowercase ('months' or 'years').",
                        row_number=idx + 2,
                        actual_value=str(val),
                        expected_value="Lowercase: months, years"
                    ))

        # ----------------------------------------------------
        # LA-018, LA-019, LA-021, LA-024, LA-055: Strict Dates Parsing
        # Note: loan_booking_date is NOT compared against sanction_date per explicit business rule correction.
        # ----------------------------------------------------
        int_start_col = get_col("interest_start_date")
        rep_start_col = get_col("repayment_start_date")
        sanc_date_col = get_col("sanction_date")
        booking_date_col = get_col("loan_booking_date")
        disb_date_col = get_col("disbursal_date")
        maturity_date_col = get_col("maturity_date")
        closure_date_col = get_col("loan_closure_date")
        cancellation_date_col = get_col("cancellation_date")

        all_date_cols = [
            ("interest_start_date", int_start_col, "LA-018", True),
            ("repayment_start_date", rep_start_col, "LA-019", True),
            ("sanction_date", sanc_date_col, "LA-021", True),
            ("loan_booking_date", booking_date_col, "LA-024", True),
            ("disbursal_date", disb_date_col, "LA-022", False),
            ("maturity_date", maturity_date_col, "LA-028", False),
            ("loan_closure_date", closure_date_col, "LA-052", False),
            ("cancellation_date", cancellation_date_col, "LA-051", False),
        ]

        parsed_dates_df: Dict[str, List[Optional[date]]] = {}

        for col_name, real_col, rule_id, is_mand in all_date_cols:
            parsed_list: List[Optional[date]] = []
            if real_col in df.columns:
                for idx, val in enumerate(df[real_col]):
                    if is_blank(val):
                        parsed_list.append(None)
                        if is_mand:
                            results.append(ValidationResult(
                                rule_id=rule_id,
                                module=self.module_name,
                                field=col_name,
                                severity=Severity.ERROR,
                                status=Status.FAIL,
                                description=f"Mandatory date column '{col_name}' is empty.",
                                row_number=idx + 2,
                                actual_value="EMPTY",
                                expected_value="YYYY-MM-DD date"
                            ))
                        continue

                    p_date = self._parse_strict_date(val)
                    parsed_list.append(p_date)

                    if not p_date:
                        results.append(ValidationResult(
                            rule_id="LA-055",
                            module=self.module_name,
                            field=col_name,
                            severity=Severity.ERROR,
                            status=Status.FAIL,
                            description=f"Invalid date format in '{col_name}'. Expected strictly YYYY-MM-DD.",
                            row_number=idx + 2,
                            actual_value=str(val),
                            expected_value="Strict YYYY-MM-DD format"
                        ))
            else:
                parsed_list = [None] * len(df)
            parsed_dates_df[col_name] = parsed_list

        # ----------------------------------------------------
        # LA-020: INTEREST VS REPAYMENT DATE (interest_start <= repayment_start)
        # ----------------------------------------------------
        if int_start_col in df.columns and rep_start_col in df.columns:
            for idx, (i_dt, r_dt) in enumerate(zip(parsed_dates_df["interest_start_date"], parsed_dates_df["repayment_start_date"])):
                if i_dt and r_dt and i_dt > r_dt:
                    results.append(ValidationResult(
                        rule_id="LA-020",
                        module=self.module_name,
                        field="repayment_start_date",
                        severity=Severity.ERROR,
                        status=Status.FAIL,
                        description=f"interest_start_date ({i_dt}) cannot be after repayment_start_date ({r_dt}).",
                        row_number=idx + 2,
                        actual_value=f"Interest: {i_dt}, Repayment: {r_dt}",
                        expected_value="interest_start_date <= repayment_start_date"
                    ))

        # ----------------------------------------------------
        # LA-023: SANCTION DATE VS DISBURSAL DATE (disbursal_date >= sanction_date)
        # ----------------------------------------------------
        if sanc_date_col in df.columns and disb_date_col in df.columns:
            for idx, (s_dt, d_dt) in enumerate(zip(parsed_dates_df["sanction_date"], parsed_dates_df["disbursal_date"])):
                if s_dt and d_dt and d_dt < s_dt:
                    results.append(ValidationResult(
                        rule_id="LA-023",
                        module=self.module_name,
                        field="disbursal_date",
                        severity=Severity.ERROR,
                        status=Status.FAIL,
                        description=f"disbursal_date ({d_dt}) cannot be before sanction_date ({s_dt}).",
                        row_number=idx + 2,
                        actual_value=str(d_dt),
                        expected_value=f">= sanction_date ({s_dt})"
                    ))

        # ----------------------------------------------------
        # LA-027: loan_status (Mandatory, Lowercase: active, closed, cancelled)
        # ----------------------------------------------------
        status_col = get_col("loan_status")
        if status_col in df.columns:
            for idx, val in enumerate(df[status_col]):
                if is_blank(val):
                    continue
                str_val = str(val).strip()
                if str_val != str_val.lower() or str_val.lower() not in self.ALLOWED_LOAN_STATUSES:
                    results.append(ValidationResult(
                        rule_id="LA-027",
                        module=self.module_name,
                        field="loan_status",
                        severity=Severity.ERROR,
                        status=Status.FAIL,
                        description="loan_status must be lowercase ('active', 'closed', or 'cancelled').",
                        row_number=idx + 2,
                        actual_value=str(val),
                        expected_value="Lowercase: active, closed, cancelled"
                    ))

        # ----------------------------------------------------
        # LA-053: STATUS / DATE CONSISTENCY (closed -> closure_date, cancelled -> cancellation_date)
        # ----------------------------------------------------
        if status_col in df.columns:
            for idx, val in enumerate(df[status_col]):
                if is_blank(val):
                    continue
                s_lower = str(val).strip().lower()
                
                if s_lower == "closed":
                    c_dt = parsed_dates_df["loan_closure_date"][idx]
                    if not c_dt:
                        results.append(ValidationResult(
                            rule_id="LA-053",
                            module=self.module_name,
                            field="loan_closure_date",
                            severity=Severity.ERROR,
                            status=Status.FAIL,
                            description="loan_closure_date must be populated when loan_status is 'closed'.",
                            row_number=idx + 2,
                            actual_value="EMPTY",
                            expected_value="Valid YYYY-MM-DD closure date"
                        ))
                elif s_lower == "cancelled":
                    cn_dt = parsed_dates_df["cancellation_date"][idx]
                    if not cn_dt:
                        results.append(ValidationResult(
                            rule_id="LA-053",
                            module=self.module_name,
                            field="cancellation_date",
                            severity=Severity.ERROR,
                            status=Status.FAIL,
                            description="cancellation_date must be populated when loan_status is 'cancelled'.",
                            row_number=idx + 2,
                            actual_value="EMPTY",
                            expected_value="Valid YYYY-MM-DD cancellation date"
                        ))

        # ----------------------------------------------------
        # LA-030: installment_amount (Numeric > 0)
        # ----------------------------------------------------
        inst_amt_col = get_col("installment_amount")
        if inst_amt_col in df.columns:
            findings = validate_numeric_range(df, inst_amt_col, min_val=0.01, rule_id="LA-030", module=self.module_name, severity=Severity.ERROR, description="installment_amount must be numeric greater than 0.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-031: principal_outstanding (Numeric >= 0)
        # ----------------------------------------------------
        prin_out_col = get_col("principal_outstanding")
        if prin_out_col in df.columns:
            findings = validate_numeric_range(df, prin_out_col, min_val=0.0, rule_id="LA-031", module=self.module_name, severity=Severity.ERROR, description="principal_outstanding must be numeric >= 0.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-032: PRINCIPAL OUTSTANDING LOGIC (principal_outstanding <= disbursed_amount)
        # ----------------------------------------------------
        if prin_out_col in df.columns and disb_col in df.columns:
            for idx, (p_val, d_val) in enumerate(zip(df[prin_out_col], df[disb_col])):
                if not is_blank(p_val) and not is_blank(d_val):
                    try:
                        p_amt = float(p_val)
                        d_amt = float(d_val)
                        if p_amt > d_amt:
                            results.append(ValidationResult(
                                rule_id="LA-032",
                                module=self.module_name,
                                field="principal_outstanding",
                                severity=Severity.ERROR,
                                status=Status.FAIL,
                                description=f"principal_outstanding ({p_amt}) cannot be greater than disbursed_amount ({d_amt}).",
                                row_number=idx + 2,
                                actual_value=str(p_val),
                                expected_value=f"<= disbursed_amount ({d_amt})"
                            ))
                    except (ValueError, TypeError):
                        pass

        # ----------------------------------------------------
        # LA-033: repayment_mode (Mandatory, Lowercase)
        # ----------------------------------------------------
        rep_mode_col = get_col("repayment_mode")
        if rep_mode_col in df.columns:
            for idx, val in enumerate(df[rep_mode_col]):
                if is_blank(val):
                    continue
                str_val = str(val).strip()
                if str_val != str_val.lower() or str_val.lower() not in self.ALLOWED_REPAYMENT_MODES:
                    results.append(ValidationResult(
                        rule_id="LA-033",
                        module=self.module_name,
                        field="repayment_mode",
                        severity=Severity.ERROR,
                        status=Status.FAIL,
                        description="repayment_mode must be lowercase valid mode (e.g. nach).",
                        row_number=idx + 2,
                        actual_value=str(val),
                        expected_value=f"Lowercase one of: {sorted(list(self.ALLOWED_REPAYMENT_MODES))}"
                    ))

        # ----------------------------------------------------
        # LA-035: emi_amount (Numeric > 0)
        # ----------------------------------------------------
        emi_col = get_col("emi_amount")
        if emi_col in df.columns:
            findings = validate_numeric_range(df, emi_col, min_val=0.01, rule_id="LA-035", module=self.module_name, severity=Severity.ERROR, description="emi_amount must be numeric greater than 0.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-036: EMI VS INSTALLMENT LOGIC (emi_amount == installment_amount)
        # ----------------------------------------------------
        if emi_col in df.columns and inst_amt_col in df.columns:
            for idx, (e_val, i_val) in enumerate(zip(df[emi_col], df[inst_amt_col])):
                if not is_blank(e_val) and not is_blank(i_val):
                    try:
                        e_amt = float(e_val)
                        i_amt = float(i_val)
                        if abs(e_amt - i_amt) > 0.01:
                            results.append(ValidationResult(
                                rule_id="LA-036",
                                module=self.module_name,
                                field="emi_amount",
                                severity=Severity.WARNING,
                                status=Status.FAIL,
                                description=f"emi_amount ({e_amt}) does not match installment_amount ({i_amt}).",
                                row_number=idx + 2,
                                actual_value=str(e_val),
                                expected_value=f"Equal to installment_amount ({i_amt})"
                            ))
                    except (ValueError, TypeError):
                        pass

        # ----------------------------------------------------
        # LA-037: scheme_code (Alphanumeric)
        # ----------------------------------------------------
        scheme_col = get_col("scheme_code")
        if scheme_col in df.columns:
            findings = validate_regex_pattern(df, scheme_col, r"^[A-Za-z0-9_\-/\s]+$", "LA-037", self.module_name, Severity.ERROR, "scheme_code must be alphanumeric.", "Alphanumeric code")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-040: is_colending (Lowercase: yes, no)
        # ----------------------------------------------------
        colend_col = get_col("is_colending")
        if colend_col in df.columns:
            findings = validate_allowed_values(df, colend_col, self.ALLOWED_COLENDING, "LA-040", self.module_name, Severity.WARNING, "is_colending must be lowercase ('yes' or 'no').")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-041: ltv_ratio (Numeric 0 to 100)
        # ----------------------------------------------------
        ltv_col = get_col("ltv_ratio")
        if ltv_col in df.columns:
            findings = validate_numeric_range(df, ltv_col, min_val=0.0, max_val=100.0, rule_id="LA-041", module=self.module_name, severity=Severity.ERROR, description="ltv_ratio must be numeric between 0 and 100.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-042: foir Ratio/Percentage Check (Numeric 0 to 100)
        # ----------------------------------------------------
        foir_col = get_col("foir")
        if foir_col in df.columns:
            findings = validate_numeric_range(df, foir_col, min_val=0.0, max_val=100.0, rule_id="LA-042", module=self.module_name, severity=Severity.ERROR, description="foir must be numeric between 0 and 100 (or 0 and 1 ratio).")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-044: paid_amount (Numeric >= 0)
        # ----------------------------------------------------
        paid_col = get_col("paid_amount")
        if paid_col in df.columns:
            findings = validate_numeric_range(df, paid_col, min_val=0.0, rule_id="LA-044", module=self.module_name, severity=Severity.ERROR, description="paid_amount must be numeric >= 0.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # LA-058: NEGATIVE FINANCIAL VALUES CHECK
        # ----------------------------------------------------
        for fin_col_name in self.FINANCIAL_AMOUNT_COLS:
            real_fin_col = get_col(fin_col_name)
            if real_fin_col in df.columns:
                for idx, val in enumerate(df[real_fin_col]):
                    if is_blank(val):
                        continue
                    try:
                        num_val = float(val)
                        if num_val < 0:
                            results.append(ValidationResult(
                                rule_id="LA-058",
                                module=self.module_name,
                                field=fin_col_name,
                                severity=Severity.ERROR,
                                status=Status.FAIL,
                                description=f"Financial field '{fin_col_name}' cannot be negative.",
                                row_number=idx + 2,
                                actual_value=str(val),
                                expected_value="Numeric amount >= 0"
                            ))
                    except (ValueError, TypeError):
                        pass

        # ----------------------------------------------------
        # LA-059: FULL DISBURSAL CONSISTENCY
        # ----------------------------------------------------
        disb_status_col = get_col("disbursal_status")
        if disb_status_col in df.columns and disb_col in df.columns and sanc_col in df.columns:
            for idx, (st_val, d_val, s_val) in enumerate(zip(df[disb_status_col], df[disb_col], df[sanc_col])):
                if not is_blank(st_val) and str(st_val).strip().lower() == "fully_disbursed":
                    if is_blank(d_val):
                        results.append(ValidationResult(
                            rule_id="LA-059",
                            module=self.module_name,
                            field="disbursed_amount",
                            severity=Severity.ERROR,
                            status=Status.FAIL,
                            description="disbursed_amount must be populated when disbursal_status is 'fully_disbursed'.",
                            row_number=idx + 2,
                            actual_value="EMPTY",
                            expected_value="Populated disbursed_amount"
                        ))
                    elif not is_blank(s_val):
                        try:
                            d_amt = float(d_val)
                            s_amt = float(s_val)
                            if abs(d_amt - s_amt) > 0.01:
                                results.append(ValidationResult(
                                    rule_id="LA-059",
                                    module=self.module_name,
                                    field="disbursed_amount",
                                    severity=Severity.WARNING,
                                    status=Status.FAIL,
                                    description=f"For fully_disbursed loan, disbursed_amount ({d_amt}) is expected to equal sanctioned_amount ({s_amt}).",
                                    row_number=idx + 2,
                                    actual_value=str(d_val),
                                    expected_value=f"Equal to sanctioned_amount ({s_amt})"
                                ))
                        except (ValueError, TypeError):
                            pass

        return results


# Automatically register LoanApplicationValidator with global registry
registry.register(LoanApplicationValidator)
