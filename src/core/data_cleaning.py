"""Generic workbook data cleaning utilities for text normalization.

This module is intentionally generic and does not include business-specific
mappings or domain logic. It only performs deterministic text normalization
operations such as trimming whitespace, removing extra spaces, reshaping
text case, and stripping line breaks or hidden characters.
"""

from __future__ import annotations

import io
import re
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd


VALID_CLEANING_OPERATIONS: List[str] = [
    "lowercase",
    "uppercase",
    "trim",
    "remove_extra_spaces",
    "remove_line_breaks",
    "remove_hidden_characters",
    "normalize_blank",
]

TEXT_ONLY_OPERATIONS = {
    "lowercase",
    "uppercase",
    "trim",
    "remove_extra_spaces",
    "remove_line_breaks",
    "remove_hidden_characters",
    "normalize_blank",
}


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        return False
    return False


def _clean_hidden_characters(value: str) -> str:
    cleaned = "".join(ch for ch in value if ch.isprintable() or ch in "\n\r\t")
    return cleaned


def _normalize_operation_list(operations: Iterable[str] | str | None) -> List[str]:
    if operations is None:
        return []
    if isinstance(operations, str):
        single_ops = [part.strip() for part in operations.split("+")]
        return [op.lower() for op in single_ops if op]

    normalized = []
    for operation in operations:
        if operation is None:
            continue
        if isinstance(operation, str):
            for part in operation.split("+"):
                cleaned = part.strip()
                if cleaned:
                    normalized.append(cleaned.lower())
        else:
            normalized.append(str(operation).strip().lower())
    return normalized


def normalize_text(value: Any, operations: Iterable[str]) -> Any:
    """Normalize a single scalar value using the selected text operations.

    Numeric and date-like values remain unchanged because this is a text
    normalization engine, not a business-value transformation engine.
    """
    if value is None:
        return None

    try:
        if pd.isna(value) and not isinstance(value, str):
            return None
    except (TypeError, ValueError):
        pass

    if not isinstance(value, str):
        return value

    text = value
    for operation in operations:
        operation_name = str(operation).strip().lower()
        if operation_name == "lowercase":
            text = text.strip().lower()
        elif operation_name == "uppercase":
            text = text.strip().upper()
        elif operation_name == "trim":
            text = text.strip()
        elif operation_name == "remove_extra_spaces":
            text = re.sub(r"\s+", " ", text).strip()
        elif operation_name == "remove_line_breaks":
            text = re.sub(r"[\r\n]+", " ", text).strip()
        elif operation_name == "remove_hidden_characters":
            text = _clean_hidden_characters(text)
            text = re.sub(r"\s+", " ", text).strip()
        elif operation_name == "normalize_blank":
            if text.strip() == "":
                return None
        else:
            raise ValueError(f"Unsupported cleaning operation: {operation}")

    if text.strip() == "":
        return None

    return text


def apply_cleaning_to_series(series: pd.Series, operations: Iterable[str]) -> pd.Series:
    """Apply selected normalization operations to a pandas Series safely.

    Only string/text values are changed; numeric, date-like, and other non-text
    values are preserved as-is.
    """
    clean_ops = _normalize_operation_list(operations)
    if not clean_ops:
        return series.copy()

    cleaned = series.astype(object).copy()
    for idx, value in series.items():
        if isinstance(value, str):
            cleaned.at[idx] = normalize_text(value, clean_ops)
        elif _is_missing_value(value):
            cleaned.at[idx] = None
        else:
            cleaned.at[idx] = value

    return cleaned


def preview_cleaning_changes(series: pd.Series, operations: Iterable[str], limit: int = 100) -> pd.DataFrame:
    """Return a preview of only rows whose text values would actually change."""
    rows: List[Dict[str, Any]] = []
    clean_ops = [str(op).strip().lower() for op in operations if str(op).strip()]
    for idx, original in series.items():
        if isinstance(original, str):
            cleaned = normalize_text(original, clean_ops)
            if cleaned != original:
                rows.append({
                    "Row": int(idx) + 2,
                    "Original": original,
                    "Cleaned": cleaned,
                })
            continue

        if _is_missing_value(original) and "normalize_blank" in clean_ops:
            if original is not None and not isinstance(original, str):
                continue
            cleaned = normalize_text(original, clean_ops)
            if cleaned != original:
                rows.append({
                    "Row": int(idx) + 2,
                    "Original": original,
                    "Cleaned": cleaned,
                })

    preview = pd.DataFrame(rows, columns=["Row", "Original", "Cleaned"])
    return preview.head(limit)


def apply_cleaning_to_workbook(
    workbook: Dict[str, pd.DataFrame],
    sheet_name: str,
    column_name: str | Iterable[str],
    operations: Iterable[str] | str,
) -> Dict[str, pd.DataFrame]:
    """Apply selected cleaning operations to one or more columns in a copied workbook."""
    cleaned_workbook = {sheet: df.copy(deep=True) for sheet, df in workbook.items()}
    if sheet_name not in cleaned_workbook:
        raise KeyError(f"Sheet '{sheet_name}' not found in workbook.")

    columns_to_clean = [column_name] if isinstance(column_name, str) else list(column_name)
    for column in columns_to_clean:
        if column not in cleaned_workbook[sheet_name].columns:
            raise KeyError(f"Column '{column}' not found in sheet '{sheet_name}'.")

    df = cleaned_workbook[sheet_name]
    for column in columns_to_clean:
        df[column] = apply_cleaning_to_series(df[column], operations)
    return cleaned_workbook


def reset_cleaning_workbook(
    cleaned_workbook: Optional[Dict[str, pd.DataFrame]],
    original_workbook: Dict[str, pd.DataFrame],
) -> Dict[str, pd.DataFrame]:
    """Restore the cleaned workbook back to its original uploaded state."""
    if original_workbook is None:
        return {}
    return {sheet: df.copy(deep=True) for sheet, df in original_workbook.items()}


def column_supports_text_cleaning(series: pd.Series) -> bool:
    """Return True when the column is text-like enough for normalization."""
    non_null = series.dropna()
    if non_null.empty:
        return True
    if pd.api.types.is_numeric_dtype(non_null) or pd.api.types.is_datetime64_any_dtype(non_null):
        return False
    values = [v for v in non_null.astype(object).tolist() if not _is_missing_value(v)]
    if not values:
        return True
    return all(isinstance(v, str) or not isinstance(v, (int, float, complex, pd.Timestamp)) for v in values)


def get_text_columns(df: pd.DataFrame) -> List[str]:
    """Return only the columns whose values are safe to normalize as text."""
    return [column for column in df.columns if column_supports_text_cleaning(df[column])]


def export_workbook_to_excel_bytes(workbook: Dict[str, pd.DataFrame]) -> bytes:
    """Serialize a workbook dictionary to an in-memory Excel file."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in workbook.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()
