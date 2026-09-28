"""
Reusable validation utility functions for tabular Excel data (Pandas Series/DataFrames).
"""

import re
from datetime import datetime
from typing import Any, List, Optional, Set, Tuple, Union
import pandas as pd


def is_blank(val: Any) -> bool:
    """Check if a value is blank, NaN, None, or empty string after stripping whitespace."""
    if pd.isna(val) or val is None:
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return False


def validate_missing_values(
    df: pd.DataFrame,
    column: str,
    rule_id: str,
    module: str,
    severity: str = "ERROR",
    description: Optional[str] = None
) -> List[dict]:
    """Find rows where a required column value is blank or missing."""
    findings = []
    if column not in df.columns:
        return findings

    desc = description or f"Mandatory column '{column}' cannot be blank or empty."

    for idx, val in enumerate(df[column]):
        if is_blank(val):
            row_num = idx + 2
            findings.append({
                "rule_id": rule_id,
                "module": module,
                "field": column,
                "severity": severity,
                "description": desc,
                "row_number": row_num,
                "actual_value": str(val) if not pd.isna(val) else "EMPTY",
                "expected_value": "Non-empty value"
            })
    return findings


def validate_regex_pattern(
    df: pd.DataFrame,
    column: str,
    pattern: str,
    rule_id: str,
    module: str,
    severity: str = "ERROR",
    description: Optional[str] = None,
    expected_format_desc: str = "Valid pattern format"
) -> List[dict]:
    """Validate string patterns against a regular expression (skips blank values)."""
    findings = []
    if column not in df.columns:
        return findings

    regex = re.compile(pattern)
    desc = description or f"Column '{column}' does not match the expected pattern format."

    for idx, val in enumerate(df[column]):
        if is_blank(val):
            continue
        
        str_val = str(val).strip()
        if not regex.match(str_val):
            row_num = idx + 2
            findings.append({
                "rule_id": rule_id,
                "module": module,
                "field": column,
                "severity": severity,
                "description": desc,
                "row_number": row_num,
                "actual_value": str_val,
                "expected_value": expected_format_desc
            })
    return findings


def validate_allowed_values(
    df: pd.DataFrame,
    column: str,
    allowed_values: Union[List[Any], Set[Any]],
    rule_id: str,
    module: str,
    severity: str = "ERROR",
    description: Optional[str] = None
) -> List[dict]:
    """Validate that column values belong to a set of allowed values (skips blank values)."""
    findings = []
    if column not in df.columns:
        return findings

    allowed_set = {str(v).strip().lower() for v in allowed_values}
    desc = description or f"Column '{column}' contains an invalid lookup/master value."

    for idx, val in enumerate(df[column]):
        if is_blank(val):
            continue
        
        str_val = str(val).strip().lower()
        if str_val not in allowed_set:
            row_num = idx + 2
            findings.append({
                "rule_id": rule_id,
                "module": module,
                "field": column,
                "severity": severity,
                "description": desc,
                "row_number": row_num,
                "actual_value": str(val),
                "expected_value": f"One of: {sorted(list(allowed_set))}"
            })
    return findings


def validate_numeric_range(
    df: pd.DataFrame,
    column: str,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    rule_id: str = "R_RANGE",
    module: str = "CORE",
    severity: str = "ERROR",
    description: Optional[str] = None
) -> List[dict]:
    """Validate numeric column values fall within [min_val, max_val] (handles % signs)."""
    findings = []
    if column not in df.columns:
        return findings

    range_desc = []
    if min_val is not None:
        range_desc.append(f">= {min_val}")
    if max_val is not None:
        range_desc.append(f"<= {max_val}")
    expected_str = " and ".join(range_desc) if range_desc else "Numeric value"

    desc = description or f"Column '{column}' numeric value out of expected bounds ({expected_str})."

    for idx, val in enumerate(df[column]):
        if is_blank(val):
            continue
        
        try:
            str_val = str(val).strip()
            if str_val.endswith("%"):
                str_val = str_val[:-1].strip()
            
            num_val = float(str_val)
            out_of_bounds = False
            if min_val is not None and num_val < min_val:
                out_of_bounds = True
            if max_val is not None and num_val > max_val:
                out_of_bounds = True
            
            if out_of_bounds:
                findings.append({
                    "rule_id": rule_id,
                    "module": module,
                    "field": column,
                    "severity": severity,
                    "description": desc,
                    "row_number": idx + 2,
                    "actual_value": str(val),
                    "expected_value": expected_str
                })
        except (ValueError, TypeError):
            findings.append({
                "rule_id": rule_id,
                "module": module,
                "field": column,
                "severity": severity,
                "description": f"Column '{column}' contains non-numeric content.",
                "row_number": idx + 2,
                "actual_value": str(val),
                "expected_value": "Valid numeric number"
            })
    return findings


def validate_duplicates(
    df: pd.DataFrame,
    columns: Union[str, List[str]],
    rule_id: str,
    module: str,
    severity: str = "ERROR",
    description: Optional[str] = None
) -> List[dict]:
    """Find duplicate rows across key columns (skips rows where all keys are blank)."""
    findings = []
    cols = [columns] if isinstance(columns, str) else columns
    
    missing_cols = [c for c in cols if c not in df.columns]
    if missing_cols:
        return findings

    col_name_str = ", ".join(cols)
    desc = description or f"Duplicate record detected for key column(s): [{col_name_str}]."

    dup_mask = df.duplicated(subset=cols, keep=False)
    
    for idx, (is_dup, row) in enumerate(zip(dup_mask, df.to_dict("records"))):
        if is_dup:
            key_vals = [row.get(c) for c in cols]
            if all(is_blank(v) for v in key_vals):
                continue
            
            val_str = ", ".join([f"{c}={row.get(c)}" for c in cols])
            findings.append({
                "rule_id": rule_id,
                "module": module,
                "field": col_name_str,
                "severity": severity,
                "description": desc,
                "row_number": idx + 2,
                "actual_value": val_str,
                "expected_value": "Unique record key"
            })
    return findings


def validate_date_format(
    df: pd.DataFrame,
    column: str,
    date_format: str,
    rule_id: str,
    module: str,
    severity: str = "ERROR",
    description: Optional[str] = None
) -> List[dict]:
    """Validate date column strings against a date format string."""
    findings = []
    if column not in df.columns:
        return findings

    desc = description or f"Column '{column}' date format is invalid."

    for idx, val in enumerate(df[column]):
        if is_blank(val):
            continue

        if isinstance(val, (pd.Timestamp, datetime)):
            continue

        str_val = str(val).strip()
        try:
            datetime.strptime(str_val, date_format)
        except ValueError:
            findings.append({
                "rule_id": rule_id,
                "module": module,
                "field": column,
                "severity": severity,
                "description": desc,
                "row_number": idx + 2,
                "actual_value": str_val,
                "expected_value": f"Date matching format: '{date_format}'"
            })
    return findings
