"""
Loan Identification and Impact Analysis Engine.

Extracts canonical loan identifiers:
- loan_application_number
- loan_id
and builds mappings across datasets/workbooks to determine:
- Total unique affected loans
- Rule-wise affected loans
- Loan-level finding drill-downs
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
import pandas as pd
from src.core.models import ValidationResult, Severity, Status
from src.core.utils import is_blank


@dataclass
class LoanFindingImpact:
    """Enriched audit finding with canonical loan identification."""
    rule_id: str
    module: str
    field_column: str
    severity: str
    status: str
    description: str
    row_number: Optional[int]
    actual_value: str
    expected_value: str
    loan_id: str = "Unresolved"
    loan_application_number: str = "Unresolved"
    canonical_loan_key: str = "Unresolved"  # Preferred unique key for counting unique loans

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Rule ID": self.rule_id,
            "Module": self.module,
            "Field/Column": self.field_column,
            "Severity": self.severity,
            "Status": self.status,
            "Description": self.description,
            "Row Number": self.row_number if self.row_number is not None else "N/A",
            "Loan ID": self.loan_id,
            "Loan Application Number": self.loan_application_number,
            "Actual Value": self.actual_value,
            "Expected Value": self.expected_value,
        }


@dataclass
class RuleLoanSummary:
    """Rule-wise affected loans and rows aggregation."""
    rule_id: str
    module: str
    description: str
    severity: str
    affected_rows_count: int
    affected_loans_count: int
    affected_loans_list: List[str] = field(default_factory=list)


@dataclass
class LoanImpactSummary:
    """Executive Loan-Level Impact Summary metrics."""
    total_findings: int
    total_affected_rows: int
    total_unique_affected_loans: int
    unique_failed_rules_count: int
    resolved_affected_loans_count: int
    unresolved_findings_count: int
    rule_summaries: List[RuleLoanSummary] = field(default_factory=list)
    loan_details_by_rule: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    all_affected_loans: List[Dict[str, Any]] = field(default_factory=list)


class LoanIdentificationEngine:
    """
    Builds canonical loan mapping and resolves loan identifiers for audit findings.
    """

    @staticmethod
    def extract_loan_mapping(df_dict_or_df) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Scans dataframe(s) (e.g. loans / Loan Application sheet) to build bidirectional mapping:
        loan_id -> loan_application_number and loan_application_number -> loan_id.
        """
        id_to_app: Dict[str, str] = {}
        app_to_id: Dict[str, str] = {}

        dfs_to_scan: List[pd.DataFrame] = []
        if isinstance(df_dict_or_df, pd.DataFrame):
            dfs_to_scan.append(df_dict_or_df)
        elif isinstance(df_dict_or_df, dict):
            for k, d in df_dict_or_df.items():
                if isinstance(d, pd.DataFrame):
                    dfs_to_scan.append(d)

        APP_COL_CANDIDATES = [
            "loan_application_number", "application_number", "loan_application_no",
            "application_no", "loan_app_no", "loan_account_no", "loan_account_number",
            "lan", "account_no"
        ]
        LID_COL_CANDIDATES = ["loan_id", "loanid", "id_loan"]

        for df in dfs_to_scan:
            if df.empty:
                continue
            cols_map = {str(c).strip().lower().replace(" ", "_"): c for c in df.columns}
            lid_col = None
            for c in LID_COL_CANDIDATES:
                if c in cols_map:
                    lid_col = cols_map[c]
                    break

            app_col = None
            for c in APP_COL_CANDIDATES:
                if c in cols_map:
                    app_col = cols_map[c]
                    break

            if lid_col and app_col:
                for _, row in df[[lid_col, app_col]].dropna().iterrows():
                    l_val = str(row[lid_col]).strip()
                    a_val = str(row[app_col]).strip()
                    if l_val and a_val and l_val.lower() != "nan" and a_val.lower() != "nan":
                        id_to_app[l_val] = a_val
                        app_to_id[a_val] = l_val

        return id_to_app, app_to_id

    @classmethod
    def resolve_finding_loan(
        cls,
        row_num: Optional[int],
        source_df: Optional[pd.DataFrame],
        id_to_app: Dict[str, str],
        app_to_id: Dict[str, str]
    ) -> Tuple[str, str, str]:
        """
        Resolves (loan_id, loan_application_number, canonical_key) for a specific row.
        Preferred order:
        1. Direct loan_application_number if available
        2. loan_id if available
        3. Existing project mapping between loan_id and loan_application_number
        4. If no valid mapping exists: 'Unresolved'
        """
        resolved_lid = "Unresolved"
        resolved_app = "Unresolved"

        APP_COL_CANDIDATES = [
            "loan_application_number", "application_number", "loan_application_no",
            "application_no", "loan_app_no", "loan_account_no", "loan_account_number",
            "lan", "account_no"
        ]
        LID_COL_CANDIDATES = ["loan_id", "loanid", "id_loan"]

        if source_df is not None and row_num is not None:
            try:
                df_idx = int(row_num) - 2
                if 0 <= df_idx < len(source_df):
                    row = source_df.iloc[df_idx]
                    cols_map = {str(c).strip().lower().replace(" ", "_"): c for c in source_df.columns}

                    # Check direct loan_application_number
                    for c in APP_COL_CANDIDATES:
                        if c in cols_map and not is_blank(row.get(cols_map[c])):
                            resolved_app = str(row.get(cols_map[c])).strip()
                            break

                    # Check direct loan_id
                    for c in LID_COL_CANDIDATES:
                        if c in cols_map and not is_blank(row.get(cols_map[c])):
                            resolved_lid = str(row.get(cols_map[c])).strip()
                            break

                    # Reconcile using mapping
                    if resolved_app != "Unresolved" and resolved_lid == "Unresolved":
                        if resolved_app in app_to_id:
                            resolved_lid = app_to_id[resolved_app]

                    if resolved_lid != "Unresolved" and resolved_app == "Unresolved":
                        if resolved_lid in id_to_app:
                            resolved_app = id_to_app[resolved_lid]
            except Exception:
                pass

        # Determine canonical key for unique counting
        if resolved_app != "Unresolved":
            canonical_key = resolved_app
        elif resolved_lid != "Unresolved":
            canonical_key = resolved_lid
        else:
            canonical_key = "Unresolved"

        return resolved_lid, resolved_app, canonical_key

    @classmethod
    def analyze_impact(
        cls,
        results: List[ValidationResult],
        source_df: Optional[pd.DataFrame] = None,
        workbook_dfs: Optional[Dict[str, pd.DataFrame]] = None,
        default_module: str = "Unknown"
    ) -> Tuple[List[LoanFindingImpact], LoanImpactSummary]:
        """
        Enriches validation results with canonical loan identifiers and computes
        executive loan-level impact analytics.
        """
        # Build lookup tables once
        dfs_for_mapping = {}
        if workbook_dfs:
            dfs_for_mapping.update(workbook_dfs)
        if source_df is not None:
            dfs_for_mapping["_current"] = source_df

        id_to_app, app_to_id = cls.extract_loan_mapping(dfs_for_mapping)

        enriched_findings: List[LoanFindingImpact] = []
        overall_unique_loans: Set[str] = set()
        unresolved_count = 0

        rule_groups: Dict[str, Dict[str, Any]] = {}

        # Filter only failing findings for impact
        failing_results = [r for r in results if r.status == Status.FAIL]

        for r in failing_results:
            curr_df = source_df
            # If multi-sheet and module matches a sheet name
            if workbook_dfs and r.module:
                mod_lower = r.module.lower().replace(" ", "_")
                for s_name, s_df in workbook_dfs.items():
                    if s_name.lower().replace(" ", "_") == mod_lower or s_name.lower() == r.module.lower():
                        curr_df = s_df
                        break

            lid, lapp, can_key = cls.resolve_finding_loan(
                row_num=r.row_number,
                source_df=curr_df,
                id_to_app=id_to_app,
                app_to_id=app_to_id
            )

            if can_key != "Unresolved":
                overall_unique_loans.add(can_key)
            else:
                unresolved_count += 1

            impact_finding = LoanFindingImpact(
                rule_id=r.rule_id,
                module=r.module or default_module,
                field_column=r.field,
                severity=r.severity.value if hasattr(r.severity, "value") else str(r.severity),
                status=r.status.value if hasattr(r.status, "value") else str(r.status),
                description=r.description,
                row_number=r.row_number,
                actual_value="" if r.actual_value is None else str(r.actual_value),
                expected_value="" if r.expected_value is None else str(r.expected_value),
                loan_id=lid,
                loan_application_number=lapp,
                canonical_loan_key=can_key
            )
            enriched_findings.append(impact_finding)

            # Accumulate Rule-wise
            rid = r.rule_id
            if rid not in rule_groups:
                rule_groups[rid] = {
                    "rule_id": rid,
                    "module": r.module or default_module,
                    "description": r.description,
                    "severity": r.severity.value if hasattr(r.severity, "value") else str(r.severity),
                    "rows": [],
                    "loans_map": {},  # can_key -> {"lid": lid, "app": lapp, "rows": []}
                }
            rg = rule_groups[rid]
            if r.row_number is not None:
                rg["rows"].append(r.row_number)

            if can_key not in rg["loans_map"]:
                rg["loans_map"][can_key] = {
                    "loan_id": lid,
                    "loan_application_number": lapp,
                    "rows": []
                }
            if r.row_number is not None:
                rg["loans_map"][can_key]["rows"].append(r.row_number)

        # Build Rule Summaries & Details
        rule_summaries: List[RuleLoanSummary] = []
        loan_details_by_rule: Dict[str, List[Dict[str, Any]]] = {}

        for rid, rg in rule_groups.items():
            valid_loans = [k for k in rg["loans_map"].keys() if k != "Unresolved"]
            affected_loans_cnt = len(valid_loans)
            if "Unresolved" in rg["loans_map"]:
                # If only unresolved exists, count 0 or represent unresolved
                pass

            rule_summaries.append(RuleLoanSummary(
                rule_id=rid,
                module=rg["module"],
                description=rg["description"],
                severity=rg["severity"],
                affected_rows_count=len(set(rg["rows"])) if rg["rows"] else len(rg["rows"]),
                affected_loans_count=affected_loans_cnt,
                affected_loans_list=valid_loans
            ))

            details = []
            for can_key, l_info in rg["loans_map"].items():
                rows_sorted = sorted(list(set(l_info["rows"])))
                rows_str = ", ".join(map(str, rows_sorted)) if rows_sorted else "N/A"
                details.append({
                    "Loan ID": l_info["loan_id"],
                    "Loan Application Number": l_info["loan_application_number"],
                    "Error Rows": rows_str,
                    "Finding Count": len(l_info["rows"])
                })
            # sort by finding count descending
            details.sort(key=lambda x: x["Finding Count"], reverse=True)
            loan_details_by_rule[rid] = details

        # Sort rule summaries by affected loans descending
        rule_summaries.sort(key=lambda x: (x.affected_loans_count, x.affected_rows_count), reverse=True)

        # Build overall unique affected loans list
        all_loans_map: Dict[str, Dict[str, Any]] = {}
        for f in enriched_findings:
            ck = f.canonical_loan_key
            if ck == "Unresolved":
                continue
            if ck not in all_loans_map:
                all_loans_map[ck] = {
                    "Loan ID": f.loan_id,
                    "Loan Application Number": f.loan_application_number,
                    "Module": f.module,
                    "Finding Count": 0,
                    "Rules Violated": set(),
                    "Affected Rows": set()
                }
            all_loans_map[ck]["Finding Count"] += 1
            all_loans_map[ck]["Rules Violated"].add(f.rule_id)
            if f.row_number is not None:
                all_loans_map[ck]["Affected Rows"].add(f.row_number)

        all_affected_loans = []
        for ck, item in all_loans_map.items():
            rows_sorted = sorted(list(item["Affected Rows"]))
            all_affected_loans.append({
                "Loan ID": item["Loan ID"],
                "Loan Application Number": item["Loan Application Number"],
                "Module": item["Module"],
                "Total Findings": item["Finding Count"],
                "Rules Violated": ", ".join(sorted(item["Rules Violated"])),
                "Affected Rows": ", ".join(map(str, rows_sorted)) if rows_sorted else "N/A"
            })
        all_affected_loans.sort(key=lambda x: x["Total Findings"], reverse=True)

        total_findings = len(failing_results)
        distinct_rows = set((f.module, f.row_number) for f in enriched_findings if f.row_number is not None)
        total_affected_rows = len(distinct_rows) if distinct_rows else total_findings
        unique_rules_count = len(rule_groups)
        total_unique_loans = len(overall_unique_loans)

        summary = LoanImpactSummary(
            total_findings=total_findings,
            total_affected_rows=total_affected_rows,
            total_unique_affected_loans=total_unique_loans,
            unique_failed_rules_count=unique_rules_count,
            resolved_affected_loans_count=total_unique_loans,
            unresolved_findings_count=unresolved_count,
            rule_summaries=rule_summaries,
            loan_details_by_rule=loan_details_by_rule,
            all_affected_loans=all_affected_loans
        )

        return enriched_findings, summary
