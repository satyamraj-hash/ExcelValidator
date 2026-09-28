"""
Collateral Migration Module Validator Implementation.

Implements validation test cases (COLL-001 through COLL-028) specified in the
enterprise migration specification. Integrates cleanly into BaseValidator and
ValidatorRegistry.
"""

import json
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Set
import pandas as pd

from src.core.base import BaseValidator, ValidationRule
from src.core.models import ValidationResult, Severity, Status
from src.core.registry import registry
from src.core.utils import (
    is_blank,
    validate_missing_values,
    validate_allowed_values,
    validate_numeric_range,
    validate_duplicates,
)


class CollateralValidator(BaseValidator):
    """
    Production-grade validation engine for Collateral Excel migration template.

    Validates 30 columns from the collateral sheet per migration spec.
    Only loan_id, collateral_type, and loan_account_number are mandatory.
    All other fields are validated only when populated (non-blank).
    """

    # Only confirmed mandatory fields per migration spec
    MANDATORY_COLS = [
        "loan_id",
        "collateral_type",
        "loan_account_number",
    ]

    COLUMN_ALIASES: Dict[str, List[str]] = {
        "property_purpose.1": ["property_purpose.1", "property_purpose_1"],
    }

    # Allowed enum values - all lowercase as stored in target DB
    ALLOWED_COLLATERAL_TYPES = {"land", "building", "vehicle", "gold", "others"}
    ALLOWED_COLLATERAL_SUBTYPES = {
        "residential", "commercial", "industrial",
        "flat", "house", "plot", "shop", "office",
        "two_wheeler", "two wheeler", "four_wheeler", "four wheeler", "truck", "tractor",
        "residential_flat", "residential_house", "residential_plot",
        "commercial_shop", "commercial_office",
    }
    ALLOWED_PROPERTY_TYPES = {
        "flat", "independent house", "independent_house", "plot",
        "residential flat", "residential_flat", "residential house", "residential_house",
        "residential plot", "residential_plot",
        "commercial flat", "commercial_flat", "commercial shop", "commercial_shop",
        "commercial office", "commercial_office",
        "agricultural land", "agricultural_land",
    }
    ALLOWED_NATURE_OF_PROPERTY = {"freehold", "leasehold"}
    ALLOWED_PROPERTY_CLASSIFICATIONS = {"residential", "commercial", "industrial", "agricultural"}
    ALLOWED_PROPERTY_OWNERSHIP = {"sole", "joint"}
    ALLOWED_PROPERTY_PURPOSES = {"self-use", "rental", "investment", "self_use"}
    ALLOWED_ADDRESS_TYPES = {"residential", "commercial", "permanent", "current", "office"}
    ALLOWED_REGIONS = {"north", "south", "east", "west"}
    ALLOWED_YES_NO = {"yes", "no"}

    @property
    def module_name(self) -> str:
        return "Collateral"

    @property
    def required_columns(self) -> List[str]:
        return self.MANDATORY_COLS

    def get_rules_metadata(self) -> List[ValidationRule]:
        return [
            ValidationRule("COLL-001", "Collateral", "loan_id", "loan_id mandatory, numeric integer & unique", Severity.ERROR),
            ValidationRule("COLL-002", "Collateral", "collateral_type", "collateral_type mandatory, lowercase valid configured value", Severity.ERROR),
            ValidationRule("COLL-003", "Collateral", "collateral_subtype", "collateral_subtype lowercase valid configured value where populated", Severity.WARNING),
            ValidationRule("COLL-004", "Collateral", "loan_account_number", "loan_account_number mandatory, alphanumeric & unique", Severity.ERROR),
            ValidationRule("COLL-005", "Collateral", "property_type", "property_type lowercase valid configured value where populated", Severity.WARNING),
            ValidationRule("COLL-006", "Collateral", "nature_of_property", "nature_of_property lowercase freehold/leasehold where populated", Severity.WARNING),
            ValidationRule("COLL-007", "Collateral", "is_building_constructed", "is_building_constructed lowercase yes/no where populated", Severity.WARNING),
            ValidationRule("COLL-008", "Collateral", "property_classification", "property_classification lowercase valid configured value where populated", Severity.WARNING),
            ValidationRule("COLL-009", "Collateral", "property_ownership", "property_ownership lowercase sole/joint where populated", Severity.WARNING),
            ValidationRule("COLL-010", "Collateral", "market_value", "market_value numeric, non-negative, > 0 where populated", Severity.ERROR),
            ValidationRule("COLL-011", "Collateral", "property_purpose", "property_purpose lowercase valid configured value where populated", Severity.WARNING),
            ValidationRule("COLL-012", "Collateral", "residual_age_of_property", "residual_age_of_property numeric non-negative where populated", Severity.WARNING),
            ValidationRule("COLL-013", "Collateral", "address_json", "address_json valid JSON object where populated", Severity.ERROR),
            ValidationRule("COLL-014", "Collateral", "is_property_registered_in_favour_of_borrower", "lowercase yes/no where populated", Severity.WARNING),
            ValidationRule("COLL-015", "Collateral", "is_security", "is_security lowercase yes/no where populated", Severity.WARNING),
            ValidationRule("COLL-016", "Collateral", "address_type", "address_type lowercase valid configured value where populated", Severity.WARNING),
            ValidationRule("COLL-017", "Collateral", "country", "country non-blank text where populated", Severity.WARNING),
            ValidationRule("COLL-018", "Collateral", "plot_number", "plot_number alphanumeric where populated", Severity.WARNING),
            ValidationRule("COLL-019", "Collateral", "pincode", "pincode exactly 6 numeric digits where populated", Severity.ERROR),
            ValidationRule("COLL-020", "Collateral", "region", "region lowercase one of north/south/east/west where populated", Severity.WARNING),
            ValidationRule("COLL-021", "Collateral", "state", "state text non-blank where populated", Severity.WARNING),
            ValidationRule("COLL-022", "Collateral", "city", "city text non-blank where populated", Severity.WARNING),
            ValidationRule("COLL-023", "Collateral", "district", "district text non-blank where populated", Severity.WARNING),
            ValidationRule("COLL-024", "Collateral", "seller_name", "seller_name text where populated", Severity.WARNING),
            ValidationRule("COLL-025", "Collateral", "present_registered_owner", "present_registered_owner text where populated", Severity.WARNING),
            ValidationRule("COLL-026", "Collateral", "built_up_area", "built_up_area numeric non-negative where populated", Severity.WARNING),
            ValidationRule("COLL-027", "Collateral", "carpet_area", "carpet_area numeric non-negative and <= built_up_area", Severity.WARNING),
            ValidationRule("COLL-028", "Collateral", "property_purpose_consistency", "property_purpose and property_purpose.1 must match where both populated", Severity.WARNING),
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
                results.append(ValidationResult(
                    rule_id="COLL_STRUCT_001",
                    module=self.module_name,
                    field=req_col,
                    severity=Severity.ERROR,
                    status=Status.FAIL,
                    description=f"Missing mandatory column '{req_col}' in uploaded file.",
                    row_number=None,
                    actual_value="COLUMN_MISSING",
                    expected_value=req_col
                ))
        return results

    def _run_validations(self, df: pd.DataFrame) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        def get_col(col_name: str) -> str:
            return self._get_matched_col(col_name, df)

        def add(rule_id, field, severity, description, row_number, actual_value, expected_value):
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

        # COLL-001: loan_id - Mandatory, Numeric Integer, Unique
        loan_id_col = get_col("loan_id")
        if loan_id_col in df.columns:
            for idx, val in enumerate(df[loan_id_col]):
                row = idx + 2
                if is_blank(val):
                    add("COLL-001", "loan_id", Severity.ERROR, "loan_id cannot be blank.", row, "EMPTY", "Integer loan ID")
                    continue
                try:
                    float_val = float(val)
                    if not float_val.is_integer():
                        add("COLL-001", "loan_id", Severity.ERROR, "loan_id must be a numeric integer (no decimals).", row, val, "Integer (e.g. 12345)")
                except (ValueError, TypeError):
                    add("COLL-001", "loan_id", Severity.ERROR, "loan_id contains non-numeric text.", row, val, "Integer (e.g. 12345)")
            findings = validate_duplicates(df, loan_id_col, "COLL-001", self.module_name, Severity.ERROR, "Duplicate loan_id found.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # COLL-002: collateral_type - Mandatory, Lowercase, Valid value
        ct_col = get_col("collateral_type")
        if ct_col in df.columns:
            findings = validate_missing_values(df, ct_col, "COLL-002", self.module_name, Severity.ERROR, "collateral_type is mandatory and cannot be blank.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))
            for idx, val in enumerate(df[ct_col]):
                if is_blank(val):
                    continue
                if str(val).strip().lower() not in self.ALLOWED_COLLATERAL_TYPES:
                    add("COLL-002", "collateral_type", Severity.ERROR,
                        f"collateral_type must be one of {sorted(self.ALLOWED_COLLATERAL_TYPES)}.",
                        idx + 2, val, f"One of: {sorted(self.ALLOWED_COLLATERAL_TYPES)}")

        # COLL-003: collateral_subtype - Optional, Valid value where populated
        cs_col = get_col("collateral_subtype")
        if cs_col in df.columns:
            for idx, val in enumerate(df[cs_col]):
                if is_blank(val):
                    continue
                if str(val).strip().lower() not in self.ALLOWED_COLLATERAL_SUBTYPES:
                    add("COLL-003", "collateral_subtype", Severity.WARNING,
                        f"collateral_subtype '{val}' is not a recognised configured value.",
                        idx + 2, val, f"e.g. {sorted(self.ALLOWED_COLLATERAL_SUBTYPES)}")

        # COLL-004: loan_account_number - Mandatory, Alphanumeric, Unique
        lan_col = get_col("loan_account_number")
        if lan_col in df.columns:
            findings = validate_missing_values(df, lan_col, "COLL-004", self.module_name, Severity.ERROR, "loan_account_number is mandatory and cannot be blank.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))
            for idx, val in enumerate(df[lan_col]):
                if is_blank(val):
                    continue
                if not re.match(r'^[A-Za-z0-9\-_/]+$', str(val).strip()):
                    add("COLL-004", "loan_account_number", Severity.ERROR, "loan_account_number must be alphanumeric.", idx + 2, val, "Alphanumeric (e.g. LN1234567890)")
            findings = validate_duplicates(df, lan_col, "COLL-004", self.module_name, Severity.ERROR, "Duplicate loan_account_number found.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # COLL-005: property_type - Optional, valid configured value
        pt_col = get_col("property_type")
        if pt_col in df.columns:
            for idx, val in enumerate(df[pt_col]):
                if is_blank(val):
                    continue
                if str(val).strip().lower() not in self.ALLOWED_PROPERTY_TYPES:
                    add("COLL-005", "property_type", Severity.WARNING,
                        f"property_type '{val}' is not a recognised configured value.",
                        idx + 2, val, f"e.g. {sorted(self.ALLOWED_PROPERTY_TYPES)}")

        # COLL-006: nature_of_property - Optional, freehold/leasehold
        np_col = get_col("nature_of_property")
        if np_col in df.columns:
            findings = validate_allowed_values(df, np_col, self.ALLOWED_NATURE_OF_PROPERTY, "COLL-006", self.module_name, Severity.WARNING, "nature_of_property must be 'freehold' or 'leasehold'.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # COLL-007: is_building_constructed - Optional, yes/no
        ibc_col = get_col("is_building_constructed")
        if ibc_col in df.columns:
            findings = validate_allowed_values(df, ibc_col, self.ALLOWED_YES_NO, "COLL-007", self.module_name, Severity.WARNING, "is_building_constructed must be 'yes' or 'no'.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # COLL-008: property_classification - Optional, valid value
        pc_col = get_col("property_classification")
        if pc_col in df.columns:
            for idx, val in enumerate(df[pc_col]):
                if is_blank(val):
                    continue
                if str(val).strip().lower() not in self.ALLOWED_PROPERTY_CLASSIFICATIONS:
                    add("COLL-008", "property_classification", Severity.WARNING,
                        f"property_classification '{val}' is not a recognised configured value.",
                        idx + 2, val, f"One of: {sorted(self.ALLOWED_PROPERTY_CLASSIFICATIONS)}")

        # COLL-009: property_ownership - Optional, sole/joint
        po_col = get_col("property_ownership")
        if po_col in df.columns:
            findings = validate_allowed_values(df, po_col, self.ALLOWED_PROPERTY_OWNERSHIP, "COLL-009", self.module_name, Severity.WARNING, "property_ownership must be 'sole' or 'joint'.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # COLL-010: market_value - Numeric, non-negative, > 0 where populated
        mv_col = get_col("market_value")
        if mv_col in df.columns:
            findings = validate_numeric_range(df, mv_col, min_val=0.01, rule_id="COLL-010", module=self.module_name, severity=Severity.ERROR, description="market_value must be numeric and > 0.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # COLL-011: property_purpose - Optional, valid configured value
        pp_col = get_col("property_purpose")
        if pp_col in df.columns:
            for idx, val in enumerate(df[pp_col]):
                if is_blank(val):
                    continue
                if str(val).strip().lower() not in self.ALLOWED_PROPERTY_PURPOSES:
                    add("COLL-011", "property_purpose", Severity.WARNING,
                        f"property_purpose '{val}' is not a recognised configured value.",
                        idx + 2, val, f"One of: {sorted(self.ALLOWED_PROPERTY_PURPOSES)}")

        # COLL-012: residual_age_of_property - Numeric non-negative where populated
        rap_col = get_col("residual_age_of_property")
        if rap_col in df.columns:
            findings = validate_numeric_range(df, rap_col, min_val=0, rule_id="COLL-012", module=self.module_name, severity=Severity.WARNING, description="residual_age_of_property must be numeric and non-negative.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # COLL-013: address_json - Valid JSON where populated
        aj_col = get_col("address_json")
        if aj_col in df.columns:
            for idx, val in enumerate(df[aj_col]):
                if is_blank(val):
                    continue
                str_val = str(val).strip()
                try:
                    parsed = json.loads(str_val)
                    if not isinstance(parsed, dict):
                        add("COLL-013", "address_json", Severity.ERROR, "address_json must be a valid JSON object (dict), not an array or primitive.", idx + 2, str_val[:80], "Valid JSON object {}")
                except (json.JSONDecodeError, ValueError):
                    add("COLL-013", "address_json", Severity.ERROR, "address_json contains invalid JSON that cannot be parsed.", idx + 2, str_val[:80], "Valid JSON object {}")

        # COLL-014: is_property_registered_in_favour_of_borrower - Optional, yes/no
        iprfob_col = get_col("is_property_registered_in_favour_of_borrower")
        if iprfob_col in df.columns:
            findings = validate_allowed_values(df, iprfob_col, self.ALLOWED_YES_NO, "COLL-014", self.module_name, Severity.WARNING, "is_property_registered_in_favour_of_borrower must be 'yes' or 'no'.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # COLL-015: is_security - Optional, yes/no
        is_col = get_col("is_security")
        if is_col in df.columns:
            findings = validate_allowed_values(df, is_col, self.ALLOWED_YES_NO, "COLL-015", self.module_name, Severity.WARNING, "is_security must be 'yes' or 'no'.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # COLL-016: address_type - Optional, valid configured value
        at_col = get_col("address_type")
        if at_col in df.columns:
            for idx, val in enumerate(df[at_col]):
                if is_blank(val):
                    continue
                if str(val).strip().lower() not in self.ALLOWED_ADDRESS_TYPES:
                    add("COLL-016", "address_type", Severity.WARNING,
                        f"address_type '{val}' is not a recognised configured value.",
                        idx + 2, val, f"One of: {sorted(self.ALLOWED_ADDRESS_TYPES)}")

        # COLL-017: country - Text, no purely-numeric values
        country_col = get_col("country")
        if country_col in df.columns:
            for idx, val in enumerate(df[country_col]):
                if is_blank(val):
                    continue
                if not re.match(r'^[A-Za-z\s\-\.]+$', str(val).strip()):
                    add("COLL-017", "country", Severity.WARNING, "country should contain only alphabetic characters.", idx + 2, val, "Country name text (e.g. India)")

        # COLL-018: plot_number - Alphanumeric where populated
        pn_col = get_col("plot_number")
        if pn_col in df.columns:
            for idx, val in enumerate(df[pn_col]):
                if is_blank(val):
                    continue
                if not re.match(r'^[A-Za-z0-9\-_/\s]+$', str(val).strip()):
                    add("COLL-018", "plot_number", Severity.WARNING, "plot_number should be alphanumeric.", idx + 2, val, "Alphanumeric (e.g. PLOT-123)")

        # COLL-019: pincode - Exactly 6 numeric digits where populated
        pincode_col = get_col("pincode")
        if pincode_col in df.columns:
            for idx, val in enumerate(df[pincode_col]):
                if is_blank(val):
                    continue
                str_val = str(val).strip()
                if '.' in str_val:
                    try:
                        fv = float(str_val)
                        if fv.is_integer():
                            str_val = str(int(fv))
                    except (ValueError, TypeError):
                        pass
                if not re.match(r'^\d{6}$', str_val):
                    add("COLL-019", "pincode", Severity.ERROR, "pincode must be exactly 6 numeric digits.", idx + 2, val, "6-digit numeric pincode (e.g. 411046)")

        # COLL-020: region - Optional, north/south/east/west
        region_col = get_col("region")
        if region_col in df.columns:
            findings = validate_allowed_values(df, region_col, self.ALLOWED_REGIONS, "COLL-020", self.module_name, Severity.WARNING, "region must be one of: north, south, east, west.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # COLL-021: state - Flag purely numeric values
        state_col = get_col("state")
        if state_col in df.columns:
            for idx, val in enumerate(df[state_col]):
                if is_blank(val):
                    continue
                if re.match(r'^\d+$', str(val).strip()):
                    add("COLL-021", "state", Severity.WARNING, "state value appears to be purely numeric, expected a state name.", idx + 2, val, "State name (e.g. Maharashtra)")

        # COLL-022: city - Flag purely numeric values
        city_col = get_col("city")
        if city_col in df.columns:
            for idx, val in enumerate(df[city_col]):
                if is_blank(val):
                    continue
                if re.match(r'^\d+$', str(val).strip()):
                    add("COLL-022", "city", Severity.WARNING, "city value appears to be purely numeric, expected a city name.", idx + 2, val, "City name (e.g. Mumbai)")

        # COLL-023: district - Flag purely numeric values
        dist_col = get_col("district")
        if dist_col in df.columns:
            for idx, val in enumerate(df[dist_col]):
                if is_blank(val):
                    continue
                if re.match(r'^\d+$', str(val).strip()):
                    add("COLL-023", "district", Severity.WARNING, "district value appears to be purely numeric, expected a district name.", idx + 2, val, "District name")

        # COLL-024: seller_name - Text where populated (min 2 chars)
        sn_col = get_col("seller_name")
        if sn_col in df.columns:
            for idx, val in enumerate(df[sn_col]):
                if is_blank(val):
                    continue
                if len(str(val).strip()) < 2:
                    add("COLL-024", "seller_name", Severity.WARNING, "seller_name is too short to be a valid name.", idx + 2, val, "Name text (e.g. Mr. Ramesh Kumar)")

        # COLL-025: present_registered_owner - Text where populated (min 2 chars)
        pro_col = get_col("present_registered_owner")
        if pro_col in df.columns:
            for idx, val in enumerate(df[pro_col]):
                if is_blank(val):
                    continue
                if len(str(val).strip()) < 2:
                    add("COLL-025", "present_registered_owner", Severity.WARNING, "present_registered_owner is too short to be a valid name.", idx + 2, val, "Name text")

        # COLL-026: built_up_area - Numeric, non-negative where populated
        bua_col = get_col("built_up_area")
        if bua_col in df.columns:
            findings = validate_numeric_range(df, bua_col, min_val=0, rule_id="COLL-026", module=self.module_name, severity=Severity.WARNING, description="built_up_area must be numeric and non-negative.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))

        # COLL-027: carpet_area - Numeric, non-negative & <= built_up_area
        ca_col = get_col("carpet_area")
        if ca_col in df.columns:
            findings = validate_numeric_range(df, ca_col, min_val=0, rule_id="COLL-027", module=self.module_name, severity=Severity.WARNING, description="carpet_area must be numeric and non-negative.")
            for f in findings:
                results.append(ValidationResult(**f, status=Status.FAIL))
            if bua_col in df.columns:
                for idx, row in df.iterrows():
                    ca_val = row.get(ca_col)
                    bua_val = row.get(bua_col)
                    if is_blank(ca_val) or is_blank(bua_val):
                        continue
                    try:
                        ca_num = float(ca_val)
                        bua_num = float(bua_val)
                        if ca_num > bua_num:
                            add("COLL-027", "carpet_area", Severity.WARNING,
                                f"carpet_area ({ca_num}) cannot exceed built_up_area ({bua_num}).",
                                idx + 2, ca_val, f"<= built_up_area ({bua_num})")
                    except (ValueError, TypeError):
                        pass

        # COLL-028: property_purpose consistency
        pp1_col = get_col("property_purpose")
        pp2_col = get_col("property_purpose.1")
        if pp1_col in df.columns and pp2_col in df.columns:
            for idx, row in df.iterrows():
                pp1_val = row.get(pp1_col)
                pp2_val = row.get(pp2_col)
                if is_blank(pp1_val) or is_blank(pp2_val):
                    continue
                if str(pp1_val).strip().lower() != str(pp2_val).strip().lower():
                    add("COLL-028", "property_purpose", Severity.WARNING,
                        f"property_purpose ('{pp1_val}') and property_purpose.1 ('{pp2_val}') must match.",
                        idx + 2, f"{pp1_val} vs {pp2_val}", "Both values must be identical")

        return results


# Auto-register on import
registry.register(CollateralValidator)
