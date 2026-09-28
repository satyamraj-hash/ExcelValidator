from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd


class TemplateKnowledgeService:
    """Read-only knowledge service backed by the actual SynoFin workbook."""

    DEFAULT_CANDIDATE_FILES = [
        r"C:\Users\satyam.raj_synoriq\Downloads\SynoFin_LMS_Migration_Template.xlsx",
        os.path.join(os.path.expanduser("~"), "Downloads", "SynoFin_LMS_Migration_Template.xlsx"),
    ]

    def __init__(self, workbook_path: Optional[str] = None):
        self.workbook_path = self._resolve_workbook_path(workbook_path)
        self.sheet_names: List[str] = []
        self.data_dictionary: List[Dict[str, Any]] = []
        self._allowed_values_by_field: Dict[str, List[str]] = {}
        self._field_index: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._readme_text: str = ""
        self._control_text: str = ""
        self._sheet_metadata: Dict[str, Dict[str, Any]] = {}

        if self.workbook_path and os.path.exists(self.workbook_path):
            self._load_from_workbook(self.workbook_path)

    def _resolve_workbook_path(self, workbook_path: Optional[str]) -> Optional[str]:
        if workbook_path:
            return workbook_path

        env_path = os.environ.get("SYNOFIN_TEMPLATE_PATH")
        if env_path and os.path.exists(env_path):
            return env_path

        for candidate in self.DEFAULT_CANDIDATE_FILES:
            if os.path.exists(candidate):
                return candidate

        workspace_root = Path.cwd()
        for candidate_name in [
            "SynoFin_LMS_Migration_Template.xlsx",
            "synofin_lms_migration_template.xlsx",
        ]:
            candidate = workspace_root / candidate_name
            if candidate.exists():
                return str(candidate)

        return None

    def _clean_value(self, value: Any) -> Any:
        if pd.isna(value):
            return None
        text = str(value).strip()
        if text == "nan" or text == "NaN":
            return None
        return text

    @staticmethod
    def _normalize_key(value: Any) -> str:
        return str(value or "").strip().lower().replace(" ", "_")

    def _load_from_workbook(self, workbook_path: str) -> None:
        workbook = pd.ExcelFile(workbook_path)
        self.sheet_names = [str(sheet).strip() for sheet in workbook.sheet_names]

        self._readme_text = self._sheet_to_text(workbook, "README")
        self._control_text = self._sheet_to_text(workbook, "CONTROL")
        self._sheet_metadata = self._build_sheet_metadata(workbook)

        data_dictionary = workbook.parse("DATA DICTIONARY", header=0)
        self.data_dictionary = self._parse_data_dictionary(data_dictionary)
        self._field_index = {
            (self._normalize_key(item["sheet"]), self._normalize_key(item["column"])): item
            for item in self.data_dictionary
        }

        self._allowed_values_by_field = self._build_allowed_values_map(workbook)
        self._sheet_metadata.update({
            sheet_name: self._sheet_metadata.get(sheet_name, {"sheet_name": sheet_name})
            for sheet_name in self.sheet_names
        })

    def _sheet_to_text(self, workbook: pd.ExcelFile, sheet_name: str) -> str:
        try:
            df = workbook.parse(sheet_name, header=None)
        except ValueError:
            return ""

        chunks: List[str] = []
        for _, row in df.iterrows():
            cells = []
            for value in row.tolist():
                cleaned = self._clean_value(value)
                if cleaned:
                    cells.append(str(cleaned))
            if cells:
                chunks.append(" ".join(cells))
        return " ".join(chunks)

    def _parse_data_dictionary(self, data_dictionary: pd.DataFrame) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for _, row in data_dictionary.iterrows():
            record = {
                "group": self._clean_value(row.get("Group")),
                "sheet": self._clean_value(row.get("Sheet")),
                "column": self._clean_value(row.get("Column (exact)")),
                "label": self._clean_value(row.get("Label")),
                "requirement": self._clean_value(row.get("Requirement")),
                "type": self._clean_value(row.get("Type")),
                "allowed_values": self._clean_value(row.get("Allowed values / format")),
                "description": self._clean_value(row.get("Description")),
                "example": self._clean_value(row.get("Example")),
            }
            if not record["sheet"] or not record["column"]:
                continue
            rows.append(record)
        return rows

    def _build_sheet_metadata(self, workbook: pd.ExcelFile) -> Dict[str, Dict[str, Any]]:
        metadata: Dict[str, Dict[str, Any]] = {}
        for sheet_name in workbook.sheet_names:
            try:
                df = workbook.parse(sheet_name, header=0)
            except Exception:
                continue

            sample_row = False
            sample_only = False
            if not df.empty:
                first_row = df.iloc[0].fillna("").astype(str)
                sample_row = bool(first_row.str.contains("SAMPLE", case=False, na=False).any())
                sample_only = sample_row and len(df) <= 2

            metadata[sheet_name] = {
                "sheet_name": sheet_name,
                "row_count": int(len(df)) if hasattr(df, "__len__") else 0,
                "column_count": int(len(df.columns)) if hasattr(df, "columns") else 0,
                "sample_row": sample_row,
                "sample_only": sample_only,
                "columns": [str(col).strip() for col in df.columns],
            }
        return metadata

    def _build_allowed_values_map(self, workbook: pd.ExcelFile) -> Dict[str, List[str]]:
        allowed_values: Dict[str, List[str]] = {}
        try:
            lists_df = workbook.parse("_lists", header=0)
        except ValueError:
            return allowed_values

        for column_name in lists_df.columns:
            values = []
            for raw in lists_df[column_name].dropna():
                cleaned = self._clean_value(raw)
                if cleaned and cleaned.lower() not in {"nan", "n/a", "none"}:
                    values.append(cleaned)
            if values:
                uniq = []
                seen = set()
                for value in values:
                    norm = str(value).strip()
                    if norm and norm.lower() not in seen:
                        uniq.append(norm)
                        seen.add(norm.lower())
                allowed_values[str(column_name).strip()] = uniq
        return allowed_values

    def get_all_sheet_names(self) -> List[str]:
        return list(self.sheet_names)

    def get_readme_knowledge(self) -> str:
        if not self._readme_text:
            return "No README metadata is available because the workbook is not present."
        prefix = "template purpose: "
        return prefix + self._readme_text[:2000]

    def get_control_knowledge(self) -> str:
        if not self._control_text:
            return "No CONTROL sheet metadata is available because the workbook is not present."
        prefix = "batch control and reconciliation: "
        return prefix + self._control_text[:2000]

    def get_data_dictionary(self) -> List[Dict[str, Any]]:
        return list(self.data_dictionary)

    def get_column_info(self, sheet_name: str, column_name: str) -> Optional[Dict[str, Any]]:
        match = self._field_index.get((self._normalize_key(sheet_name), self._normalize_key(column_name)))
        if match:
            return match
        for item in self.data_dictionary:
            if self._normalize_key(item.get("sheet")) == self._normalize_key(sheet_name) and self._normalize_key(item.get("column")) == self._normalize_key(column_name):
                return item
        return None

    def get_sheet_info(self, sheet_name: str) -> Optional[Dict[str, Any]]:
        entry = self._sheet_metadata.get(sheet_name)
        if entry is not None:
            return entry
        for candidate in self.sheet_names:
            if self._normalize_key(candidate) == self._normalize_key(sheet_name):
                return self._sheet_metadata.get(candidate)
        return None

    def get_allowed_values_for_field(self, field_name: str) -> List[str]:
        normalized = str(field_name).strip()
        if not normalized:
            return []

        if normalized in self._allowed_values_by_field:
            return list(self._allowed_values_by_field[normalized])

        lower_name = normalized.lower()
        for key, values in self._allowed_values_by_field.items():
            if key.lower() == lower_name:
                return list(values)

        for item in self.data_dictionary:
            if self._normalize_key(item.get("column")) == self._normalize_key(normalized):
                allowed = item.get("allowed_values")
                if allowed:
                    return self._parse_allowed_values(allowed)
        return []

    def get_allowed_values(self, sheet_name: str, column_name: str) -> List[str]:
        info = self.get_column_info(sheet_name, column_name)
        if info and info.get("allowed_values"):
            return self._parse_allowed_values(info["allowed_values"])
        return self.get_allowed_values_for_field(column_name)

    def _parse_allowed_values(self, allowed_value_text: str) -> List[str]:
        if not allowed_value_text:
            return []
        text = str(allowed_value_text).strip()
        if text.lower().startswith("allowed:"):
            text = text.split("Allowed:", 1)[1].strip()
        if text.lower().startswith("master:"):
            return []
        values = re.split(r"[,;\|]", text)
        cleaned = []
        seen = set()
        for value in values:
            candidate = value.strip().strip("[](){}\"'")
            if not candidate:
                continue
            candidate = candidate.replace("Allowed", "").strip()
            candidate = candidate.replace(" / ", "/")
            if candidate.lower() not in seen:
                cleaned.append(candidate)
                seen.add(candidate.lower())
        return cleaned

    def get_relationships(self, sheet_name: str) -> List[str]:
        normalized = self._normalize_key(sheet_name)
        relationships = [
            "loan_application_number is the linking key across the workbook",
            "same LAN must be repeated on every sheet for each loan",
        ]

        if normalized in {"customers", "related_people", "bank_details", "nach_detail", "disbursal_schedule", "disbursal_breakup", "repayment_schedule"}:
            relationships.append("cust_idx / bank_idx / disbursal_number are serial identifiers used to join child rows")
        if normalized == "bank_details":
            relationships.append("bank_idx links bank_details to nach_detail and other bank-linked child records")
        if normalized == "nach_detail":
            relationships.append("nach_detail.bank_idx = bank_details.bank_idx and loan_application_number ties the record to the customer loan")
        if normalized == "disbursal_schedule":
            relationships.append("disbursal_schedule.disbursal_number links to disbursal_breakup.disbursal_number")
        if normalized == "repayment_schedule":
            relationships.append("repayment_schedule.status controls outstanding, overdue and DPD calculations")
        if normalized == "customers":
            relationships.append("customers.cust_idx and customers.customer_type separate the serial number from the role of the person")
        return relationships

    def search_template_knowledge(self, query: str) -> List[str]:
        if not query or not str(query).strip():
            return ["Information is not defined in the migration template."]

        q = str(query).strip().lower()
        if not q:
            return ["Information is not defined in the migration template."]
        tokens = [token for token in re.split(r"[^a-z0-9_]+", q) if token.strip()]
        if not tokens:
            return ["Information is not defined in the migration template."]

        hits: List[str] = []

        for entry in self.data_dictionary:
            haystack = " ".join(
                [
                    str(entry.get("sheet") or ""),
                    str(entry.get("column") or ""),
                    str(entry.get("label") or ""),
                    str(entry.get("description") or ""),
                    str(entry.get("allowed_values") or ""),
                    str(entry.get("example") or ""),
                ]
            ).lower()
            if q in haystack or all(token in haystack for token in tokens):
                hits.append(
                    f"{entry.get('sheet')}::{entry.get('column')} - {entry.get('description') or entry.get('label') or 'template field'}"
                )

        if not hits:
            for field_name, values in self._allowed_values_by_field.items():
                haystack = " ".join([field_name, *values]).lower()
                if q in haystack or all(token in haystack for token in tokens):
                    hits.append(f"{field_name}: {', '.join(values[:8])}")

        if not hits:
            combined = " ".join([self._readme_text, self._control_text]).lower()
            if q in combined or all(token in combined for token in tokens):
                hits.append("README / CONTROL: workbook guidance on the matching migration rule or template requirement")

        if not hits:
            return ["Information is not defined in the migration template."]
        return hits[:10]
