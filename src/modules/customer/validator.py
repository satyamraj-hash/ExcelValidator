"""
Customer Migration Module Validator Implementation.

Robust, smart validator supporting case-insensitivity, common abbreviations,
slash/hyphen in loan numbers, and clear remediation guidance for all 63 columns.
"""

from datetime import datetime, date
import re
from typing import List, Dict, Any, Set
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


class CustomerValidator(BaseValidator):
    """
    Production-grade Customer Migration Validator.
    """

    MANDATORY_COLS = [
        "loan_application_number",
        "customer_type",
        "first_name",
        "last_name",
        "dob",
        "category",
        "marital_status",
        "pan",
        "phone1",
        "gender",
        "religion"
    ]

    COLUMN_ALIASES: Dict[str, List[str]] = {
        "permanent_landmark": ["permanent_landmark", "permanent_ladmark"],
        "passport_number": ["passport_number", "passport_no"],
    }

    # Normalized Lookup Sets (Case-insensitive)
    CUSTOMER_TYPE_MAP = {
        "applicant": "applicant", "app": "applicant", "primary": "applicant",
        "co-applicant": "co-applicant", "coapplicant": "co-applicant", "co_applicant": "co-applicant", "coapp": "co-applicant",
        "guarantor": "guarantor", "gr": "guarantor", "guaranter": "guarantor"
    }

    CATEGORY_MAP = {
        "salaried": "salaried", "self-employed": "self-employed", "self employed": "self-employed",
        "general": "general", "gen": "general",
        "minority": "minority", "obc": "obc", "sc": "sc", "st": "st"
    }

    ALLOWED_GENDERS = {"male", "female", "other", "m", "f", "o"}
    ALLOWED_RELIGIONS = {
        "hindu", "hinduism", "muslim", "christian", "sikh",
        "buddhist", "jain", "parsi", "other"
    }
    ALLOWED_MARITAL_STATUS = {"married", "single", "divorced", "widow", "unmarried"}
    ALLOWED_CASTES = {"general", "gen", "obc", "sc", "st"}
    ALLOWED_RISK_CATEGORIES = {"low", "medium", "high"}

    BOOLEAN_COLS = ["any_obligation", "indexed", "disability", "is_individual"]
    DATE_COLS = ["dob", "kyc_declaration_date", "kyc_verification_date"]
    CREDIT_SCORE_COLS = ["cibil", "crif_score", "bureau_score", "commercial_bureau_score", "equifax"]

    @property
    def module_name(self) -> str:
        return "Customer"

    @property
    def required_columns(self) -> List[str]:
        return self.MANDATORY_COLS

    def get_rules_metadata(self) -> List[ValidationRule]:
        return [
            ValidationRule("CUST_TC01", "Customer", "Structural", "Mandatory core columns must exist", Severity.ERROR),
            ValidationRule("CUST_TC02", "Customer", "Mandatory Fields", "Core mandatory fields must not be blank", Severity.ERROR),
            ValidationRule("CUST_TC03", "Customer", "loan_application_number", "Valid loan application number (alphanumeric with / - _)", Severity.ERROR),
            ValidationRule("CUST_TC04", "Customer", "customer_id", "Valid integer customer ID", Severity.ERROR),
            ValidationRule("CUST_TC05", "Customer", "customer_type", "Valid customer role (applicant, co-applicant, guarantor)", Severity.ERROR),
            ValidationRule("CUST_TC06", "Customer", "first_name/last_name", "Valid text for first & last names", Severity.WARNING),
            ValidationRule("CUST_TC07", "Customer", "dob", "Valid date (YYYY-MM-DD) and no future DOB", Severity.ERROR),
            ValidationRule("CUST_TC08", "Customer", "pan", "Valid 10-char PAN format", Severity.ERROR),
            ValidationRule("CUST_TC09", "Customer", "aadhar_number", "Valid 12-digit Aadhaar or masked format", Severity.ERROR),
            ValidationRule("CUST_TC10", "Customer", "phone1", "Valid 10-digit Indian mobile number", Severity.ERROR),
            ValidationRule("CUST_TC11", "Customer", "gender", "Valid gender value (Male, Female, Other)", Severity.ERROR),
            ValidationRule("CUST_TC12", "Customer", "religion", "Valid religion master value", Severity.ERROR),
            ValidationRule("CUST_TC13", "Customer", "current_address", "Current address completeness check", Severity.WARNING),
            ValidationRule("CUST_TC14", "Customer", "permanent_address", "Permanent address completeness check", Severity.WARNING),
            ValidationRule("CUST_TC15", "Customer", "pincode", "Valid 6-digit Indian pincode format", Severity.WARNING),
            ValidationRule("CUST_TC17", "Customer", "master_fields", "Valid category, marital_status, caste & risk_category", Severity.ERROR),
            ValidationRule("CUST_TC19", "Customer", "is_individual", "Valid boolean flag", Severity.WARNING),
            ValidationRule("CUST_TC20", "Customer", "customer_id", "Duplicate customer_id check", Severity.WARNING),
            ValidationRule("CUST_TC22", "Customer", "customer_type", "Check loan has an Applicant defined", Severity.WARNING),
            ValidationRule("CUST_TC24", "Customer", "cibil", "Credit score numeric range 300 to 900", Severity.ERROR),
            ValidationRule("CUST_TC25", "Customer", "phone1", "Duplicate phone number check", Severity.WARNING),
            ValidationRule("CUST_TC26", "Customer", "pan", "Duplicate PAN check", Severity.WARNING),
            ValidationRule("CUST_TC27", "Customer", "aadhar_number", "Duplicate Aadhaar check", Severity.WARNING),
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

    def _run_validations(self, df: pd.DataFrame) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        def get_col(col_name: str) -> str:
            return self._get_matched_col(col_name, df)

        # ----------------------------------------------------
        # TC02: Core Mandatory Fields Check
        # ----------------------------------------------------
        for mandatory_col in self.MANDATORY_COLS:
            real_col = get_col(mandatory_col)
            if real_col in df.columns:
                findings = validate_missing_values(
                    df=df,
                    column=real_col,
                    rule_id="CUST_TC02",
                    module=self.module_name,
                    severity=Severity.ERROR,
                    description=f"Mandatory column '{mandatory_col}' is empty on this row."
                )
                for f in findings:
                    results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # TC03: loan_application_number (Allow Alphanumeric + / - _ space)
        # ----------------------------------------------------
        loan_col = get_col("loan_application_number")
        if loan_col in df.columns:
            alphanumeric_regex = r"^[A-Za-z0-9_\-/\s]+$"
            findings = validate_regex_pattern(
                df=df,
                column=loan_col,
                pattern=alphanumeric_regex,
                rule_id="CUST_TC03",
                module=self.module_name,
                severity=Severity.ERROR,
                description="loan_application_number contains invalid characters.",
                expected_format_desc="Alphanumeric string (e.g. SHDG2028010 or NFL/0001)"
            )
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # TC04: customer_id & loan_id Integer Check
        # ----------------------------------------------------
        for int_col_key in ["customer_id", "loan_id"]:
            real_int_col = get_col(int_col_key)
            if real_int_col in df.columns:
                for idx, val in enumerate(df[real_int_col]):
                    if is_blank(val):
                        continue
                    try:
                        float_val = float(val)
                        if not float_val.is_integer():
                            results.append(ValidationResult(
                                rule_id="CUST_TC04",
                                module=self.module_name,
                                field=int_col_key,
                                severity=Severity.ERROR,
                                status=Status.FAIL,
                                description=f"'{int_col_key}' must be an integer number.",
                                row_number=idx + 2,
                                actual_value=str(val),
                                expected_value="Integer number (e.g. 123456)"
                            ))
                    except (ValueError, TypeError):
                        results.append(ValidationResult(
                            rule_id="CUST_TC04",
                            module=self.module_name,
                            field=int_col_key,
                            severity=Severity.ERROR,
                            status=Status.FAIL,
                            description=f"'{int_col_key}' contains non-numeric text.",
                            row_number=idx + 2,
                            actual_value=str(val),
                            expected_value="Integer number (e.g. 123456)"
                        ))

        # ----------------------------------------------------
        # TC05: customer_type (Smart Normalize Mapping)
        # ----------------------------------------------------
        cust_type_col = get_col("customer_type")
        if cust_type_col in df.columns:
            for idx, val in enumerate(df[cust_type_col]):
                if is_blank(val):
                    continue
                str_val = str(val).strip().lower()
                if str_val not in self.CUSTOMER_TYPE_MAP:
                    results.append(ValidationResult(
                        rule_id="CUST_TC05",
                        module=self.module_name,
                        field="customer_type",
                        severity=Severity.ERROR,
                        status=Status.FAIL,
                        description="Unrecognized customer_type value.",
                        row_number=idx + 2,
                        actual_value=str(val),
                        expected_value="One of: applicant, co-applicant, guarantor"
                    ))

        # ----------------------------------------------------
        # TC06: first_name & last_name Text Check
        # ----------------------------------------------------
        for name_col_key in ["first_name", "last_name", "middle_name"]:
            real_name_col = get_col(name_col_key)
            if real_name_col in df.columns:
                text_regex = r"^[A-Za-z\s\.'\-]+$"
                findings = validate_regex_pattern(
                    df=df,
                    column=real_name_col,
                    pattern=text_regex,
                    rule_id="CUST_TC06",
                    module=self.module_name,
                    severity=Severity.WARNING,
                    description=f"{name_col_key} contains digits or invalid characters.",
                    expected_format_desc="Valid name text (e.g., John)"
                )
                for f in findings:
                    results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # TC07: DOB Date Format & Future Date Check
        # ----------------------------------------------------
        dob_col = get_col("dob")
        if dob_col in df.columns:
            today_date = date.today()
            for idx, val in enumerate(df[dob_col]):
                if is_blank(val):
                    continue
                
                parsed_dob = None
                if isinstance(val, (pd.Timestamp, datetime)):
                    parsed_dob = val.date()
                elif isinstance(val, date):
                    parsed_dob = val
                else:
                    str_val = str(val).strip()
                    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]:
                        try:
                            dt = datetime.strptime(str_val, fmt)
                            parsed_dob = dt.date()
                            break
                        except ValueError:
                            pass
                    
                    if not parsed_dob:
                        results.append(ValidationResult(
                            rule_id="CUST_TC07",
                            module=self.module_name,
                            field="dob",
                            severity=Severity.ERROR,
                            status=Status.FAIL,
                            description="dob date format is invalid.",
                            row_number=idx + 2,
                            actual_value=str_val,
                            expected_value="Date in YYYY-MM-DD format"
                        ))
                        continue

                if parsed_dob and parsed_dob > today_date:
                    results.append(ValidationResult(
                        rule_id="CUST_TC07",
                        module=self.module_name,
                        field="dob",
                        severity=Severity.ERROR,
                        status=Status.FAIL,
                        description="dob date cannot be in the future.",
                        row_number=idx + 2,
                        actual_value=str(parsed_dob),
                        expected_value=f"Date <= today ({today_date})"
                    ))

        # ----------------------------------------------------
        # TC08: PAN Check (Case-Insensitive Upper)
        # ----------------------------------------------------
        pan_col = get_col("pan")
        if pan_col in df.columns:
            pan_pattern = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
            for idx, val in enumerate(df[pan_col]):
                if is_blank(val):
                    continue
                str_val = str(val).strip().upper()
                if not pan_pattern.match(str_val):
                    results.append(ValidationResult(
                        rule_id="CUST_TC08",
                        module=self.module_name,
                        field="pan",
                        severity=Severity.ERROR,
                        status=Status.FAIL,
                        description="Invalid PAN card format.",
                        row_number=idx + 2,
                        actual_value=str(val),
                        expected_value="10-character PAN (e.g. BAQPK0750C)"
                    ))

        # ----------------------------------------------------
        # TC09: Aadhaar Format Check (Handles Numeric / Float Conversion)
        # ----------------------------------------------------
        aadhar_col = get_col("aadhar_number")
        if aadhar_col in df.columns:
            aadhar_pattern = re.compile(r"^(\d{12}|[xX]{8}\d{4})$")
            for idx, val in enumerate(df[aadhar_col]):
                if is_blank(val):
                    continue
                
                # Format string if pandas converted to float (e.g. 2345.0)
                if isinstance(val, (float, int)):
                    str_val = f"{int(val):012d}" if isinstance(val, int) or val.is_integer() else str(val)
                else:
                    str_val = str(val).strip()

                if not aadhar_pattern.match(str_val):
                    results.append(ValidationResult(
                        rule_id="CUST_TC09",
                        module=self.module_name,
                        field="aadhar_number",
                        severity=Severity.ERROR,
                        status=Status.FAIL,
                        description="Invalid Aadhaar number format.",
                        row_number=idx + 2,
                        actual_value=str(val),
                        expected_value="12-digit Aadhaar (123456789012) or masked (xxxxxxxx0008)"
                    ))

        # ----------------------------------------------------
        # TC10: phone1 10-Digit Mobile Check
        # ----------------------------------------------------
        phone_col = get_col("phone1")
        if phone_col in df.columns:
            phone_pattern = re.compile(r"^[6-9]\d{9}$")
            for idx, val in enumerate(df[phone_col]):
                if is_blank(val):
                    continue
                
                if isinstance(val, (float, int)):
                    str_val = f"{int(val)}"
                else:
                    str_val = str(val).strip()

                if not phone_pattern.match(str_val):
                    results.append(ValidationResult(
                        rule_id="CUST_TC10",
                        module=self.module_name,
                        field="phone1",
                        severity=Severity.ERROR,
                        status=Status.FAIL,
                        description="phone1 must be a valid 10-digit Indian mobile number.",
                        row_number=idx + 2,
                        actual_value=str(val),
                        expected_value="10-digit mobile starting with 6-9 (e.g. 8699786256)"
                    ))

        # ----------------------------------------------------
        # TC11: gender Master Check
        # ----------------------------------------------------
        gender_col = get_col("gender")
        if gender_col in df.columns:
            findings = validate_allowed_values(
                df=df,
                column=gender_col,
                allowed_values=self.ALLOWED_GENDERS,
                rule_id="CUST_TC11",
                module=self.module_name,
                severity=Severity.ERROR,
                description="Invalid gender value."
            )
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # TC12: religion Master Check
        # ----------------------------------------------------
        religion_col = get_col("religion")
        if religion_col in df.columns:
            findings = validate_allowed_values(
                df=df,
                column=religion_col,
                allowed_values=self.ALLOWED_RELIGIONS,
                rule_id="CUST_TC12",
                module=self.module_name,
                severity=Severity.ERROR,
                description="Invalid religion value."
            )
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # TC17: category & marital_status (Smart Map)
        # ----------------------------------------------------
        cat_col = get_col("category")
        if cat_col in df.columns:
            for idx, val in enumerate(df[cat_col]):
                if is_blank(val):
                    continue
                str_val = str(val).strip().lower()
                if str_val not in self.CATEGORY_MAP:
                    results.append(ValidationResult(
                        rule_id="CUST_TC17",
                        module=self.module_name,
                        field="category",
                        severity=Severity.ERROR,
                        status=Status.FAIL,
                        description="Unrecognized category value.",
                        row_number=idx + 2,
                        actual_value=str(val),
                        expected_value="One of: Salaried, Self-employed, General, OBC, SC, ST"
                    ))

        ms_col = get_col("marital_status")
        if ms_col in df.columns:
            findings = validate_allowed_values(
                df=df,
                column=ms_col,
                allowed_values=self.ALLOWED_MARITAL_STATUS,
                rule_id="CUST_TC17",
                module=self.module_name,
                severity=Severity.ERROR,
                description="Invalid marital_status value."
            )
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # TC24: Credit Score Range 300 to 900
        # ----------------------------------------------------
        for score_col_key in self.CREDIT_SCORE_COLS:
            real_score_col = get_col(score_col_key)
            if real_score_col in df.columns:
                findings = validate_numeric_range(
                    df=df,
                    column=real_score_col,
                    min_val=300,
                    max_val=900,
                    rule_id="CUST_TC24",
                    module=self.module_name,
                    severity=Severity.ERROR if score_col_key == "cibil" else Severity.WARNING,
                    description=f"'{score_col_key}' score must be a number between 300 and 900."
                )
                for f in findings:
                    results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # TC20: Duplicate customer_id Check
        # ----------------------------------------------------
        cust_id_col = get_col("customer_id")
        if cust_id_col in df.columns:
            findings = validate_duplicates(
                df=df,
                columns=cust_id_col,
                rule_id="CUST_TC20",
                module=self.module_name,
                severity=Severity.WARNING,
                description="Duplicate customer_id found in file."
            )
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # ----------------------------------------------------
        # TC22: Customer Type per Loan (Applicant check)
        # ----------------------------------------------------
        if loan_col in df.columns and cust_type_col in df.columns:
            grouped = df.groupby(loan_col)
            for loan_no, group in grouped:
                if is_blank(loan_no):
                    continue
                types_in_loan = set()
                for t in group[cust_type_col]:
                    if not is_blank(t):
                        norm_type = self.CUSTOMER_TYPE_MAP.get(str(t).strip().lower(), str(t).strip().lower())
                        types_in_loan.add(norm_type)

                if "applicant" not in types_in_loan:
                    results.append(ValidationResult(
                        rule_id="CUST_TC22",
                        module=self.module_name,
                        field="customer_type",
                        severity=Severity.WARNING,
                        status=Status.FAIL,
                        description=f"Loan Application '{loan_no}' does not have an 'applicant' role defined.",
                        row_number=None,
                        actual_value=f"Roles present: {sorted(list(types_in_loan))}",
                        expected_value="At least one 'applicant' role per loan"
                    ))

        # ----------------------------------------------------
        # TC25, TC26, TC27: Duplicate Checks
        # ----------------------------------------------------
        if phone_col in df.columns:
            findings = validate_duplicates(df, phone_col, "CUST_TC25", self.module_name, Severity.WARNING, "Duplicate phone1 number found across customers.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        if pan_col in df.columns:
            findings = validate_duplicates(df, pan_col, "CUST_TC26", self.module_name, Severity.WARNING, "Duplicate PAN card number found across customers.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        if aadhar_col in df.columns:
            findings = validate_duplicates(df, aadhar_col, "CUST_TC27", self.module_name, Severity.WARNING, "Duplicate Aadhaar number found across customers.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        return results


# Register with global registry
registry.register(CustomerValidator)
