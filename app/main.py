"""
SynoFin LMS Migration Validator - Streamlit Enterprise Dashboard.
Matches SynoFin Loan Management System Branding & Typography.
"""

import sys
import io
import hashlib
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st

# Add project root directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.registry import registry
from src.core.models import ValidationSummary, Severity, Status
from src.core.report_generator import generate_excel_report, generate_multi_sheet_excel_report
from src.core.loan_impact import LoanIdentificationEngine
from src.core.data_cleaning import (
    VALID_CLEANING_OPERATIONS,
    apply_cleaning_to_workbook,
    column_supports_text_cleaning,
    export_workbook_to_excel_bytes,
    get_text_columns,
    preview_cleaning_changes,
    reset_cleaning_workbook,
)
from src.assistant.service import AuditContext
from src.assistant.ui import render_floating_audit_assistant

# Import validator modules to trigger automatic registration
import src.modules.customer.validator
import src.modules.loan_application.validator
import src.modules.collateral.validator
import src.modules.repayment_schedule.validator
import src.modules.bank_details.validator
import src.modules.disbursal_schedule.validator
import src.modules.nach_detail.validator
import src.modules.disbursal_breakup.validator
import src.modules.charges.validator
import src.modules.receipts.validator
import src.modules.related_people.validator
import src.modules.obligations.validator
import src.modules.business.validator
import src.modules.institution.validator
import src.modules.income_information.validator
import src.modules.expense_information.validator
import src.modules.customer_insurance.validator
import src.modules.collateral_property.validator
import src.modules.collateral_vehicle.validator
import src.modules.collateral_gold.validator
import src.modules.excess_money.validator
import src.modules.payments.validator
import src.modules.classification_history.validator
import src.modules.spdc.validator
import src.modules.upi_mandate.validator
import src.modules.gst_verification.validator
import src.modules.documents.validator
import src.modules.moratorium_details.validator
import src.modules.colending_details.validator
import src.modules.subvention.validator

def _uploaded_file_cache_key(uploaded_file):
    if uploaded_file is None:
        return None
    file_bytes = uploaded_file.getvalue()
    digest = hashlib.md5(file_bytes).hexdigest()
    return (uploaded_file.name, uploaded_file.size, digest)


@st.cache_data(show_spinner=False)
def _read_excel_bytes_cached(file_name: str, file_size: int, file_hash: str, file_bytes: bytes):
    return pd.read_excel(io.BytesIO(file_bytes))


@st.cache_data(show_spinner=False)
def _read_workbook_bytes_cached(file_name: str, file_size: int, file_hash: str, file_bytes: bytes):
    return pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)


# ----------------------------------------------------
# SynoFin LMS Corporate Page Configuration & Styling
# ----------------------------------------------------
st.set_page_config(
    page_title="Synoriq Migrator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom SynoFin Dark Blue/Navy theme styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        color: #0f172a;
    }

    .stApp {
        background: #f3f4f6;
    }

    header[data-testid="stHeader"] {
        display: none !important;
    }

    div[data-testid="stToolbar"] {
        display: none !important;
    }

    div[data-testid="stAppViewContainer"] {
        background: #f3f4f6;
    }

    section.main > div {
        padding-top: 0 !important;
    }

    .block-container {
        padding-top: 0.3rem !important;
        padding-bottom: 0.8rem;
        max-width: 100% !important;
    }

    .syno-header {
        background: #ffffff;
        border: 1px solid #dfe3e8;
        border-radius: 10px;
        padding: 16px 20px 14px 20px;
        margin: 0 0 12px 0;
        color: #0f172a;
        display: flex;
        justify-content: space-between;
        align-items: center;
        min-height: 86px;
        width: 100%;
        box-sizing: border-box;
        box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.01);
        overflow: visible;
    }

    .syno-header .left-wrap {
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 8px;
    }

    .syno-title-row {
        display: flex;
        align-items: center;
        gap: 10px;
        min-height: 32px;
    }

    .syno-logo {
        width: 18px;
        height: 18px;
        display: inline-block;
        background: linear-gradient(135deg, #f97316 0%, #f59e0b 100%);
        clip-path: polygon(0 0, 100% 50%, 0 100%);
        border-radius: 3px;
        box-shadow: 0 2px 4px rgba(249, 115, 22, 0.18);
    }

    .syno-title {
        font-size: 22px;
        font-weight: 800;
        letter-spacing: -0.05em;
        color: #111827;
        display: flex;
        align-items: center;
        gap: 0;
        line-height: 1.1;
    }

    .syno-title .brand-name {
        font-weight: 900;
        letter-spacing: -0.05em;
    }

    .syno-title .brand-accent {
        color: #1d4ed8;
        font-weight: 800;
    }

    .syno-badge {
        background: #dfeeff;
        color: #2a5ad8;
        border-radius: 999px;
        padding: 6px 10px;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-left: 8px;
        white-space: nowrap;
    }

    .syno-subtitle {
        color: #475569;
        font-size: 13px;
        margin-left: 28px;
        line-height: 1.4;
    }

    .target-box {
        text-align: right;
        min-width: 180px;
    }

    .target-label {
        font-size: 10px;
        color: #687385;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-bottom: 4px;
    }

    .target-value {
        font-size: 15px;
        color: #111827;
        font-weight: 700;
    }

    .syno-sidebar-header {
        padding: 12px 0 18px 0;
        border-bottom: 1px solid #e2e8f0;
        margin-bottom: 18px;
    }

    .syno-sidebar-title {
        font-size: 16px;
        font-weight: 700;
        color: #102a43;
    }

    .syno-sidebar-sub {
        font-size: 12px;
        color: #64748b;
    }

    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #2563eb;
        border-radius: 12px;
        padding: 16px;
    }

    .pill-error {
        background: #fee2e2;
        color: #991b1b;
        padding: 4px 8px;
        border-radius: 999px;
        font-size: 10px;
        font-weight: 700;
    }

    .pill-warning {
        background: #fef3c7;
        color: #92400e;
        padding: 4px 8px;
        border-radius: 999px;
        font-size: 10px;
        font-weight: 700;
    }

    .fix-guidance-box {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-left: 4px solid #2563eb;
        border-radius: 10px;
        padding: 12px 16px;
        margin-top: 8px;
        color: #1e40af;
        font-size: 13px;
    }

    .audit-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        font-family: 'SFMono-Regular', Consolas, monospace;
        font-size: 12px;
        color: #334155;
    }
    </style>

    <div class="syno-header">
        <div class="left-wrap">
            <div class="syno-title-row">
                <span class="syno-logo" aria-hidden="true"></span>
                <div class="syno-title">
                    <span class="brand-name">SYNORIQ</span>
                    <span class="brand-accent"> migrator</span>
                </div>
                <span class="syno-badge">Preprod Audit Engine</span>
            </div>
            <div class="syno-subtitle">
                Loan Management System Data Migration &amp; Business Rule Audit Tool
            </div>
        </div>
        <div class="target-box">
            <div class="target-label">Target System</div>
            <div class="target-value">Synoriq Migrator (Preprod)</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


def get_validator_for_sheet(sheet_name: str):
    """Resolve validator for an Excel sheet name."""
    s_norm = sheet_name.strip().lower()
    
    # Direct alias overrides for specific sheet names
    sheet_alias_map = {
        "loans": "Loan Application",
        "customers": "Customer",
        "repayment_schedule": "Repayment Schedule",
        "bank_details": "Bank Details",
        "disbursal_schedule": "Disbursal Schedule",
        "disbursal_breakup": "Disbursal Breakup",
        "charges": "Charges",
        "receipts": "Receipts",
        "related_people": "Related People",
        "obligations": "Obligations",
        "business": "Business",
        "institution": "Institution",
        "income_information": "Income Information",
        "expense_information": "Expense Information",
        "customer_insurance": "Customer Insurance",
        "collateral_property": "Collateral Property",
        "collateral_vehicle": "Collateral Vehicle",
        "collateral_gold": "Collateral Gold",
        "excess_money": "Excess Money",
        "payments": "Payments",
        "classification_history": "Classification History",
        "spdc": "Spdc",
        "upi_mandate": "Upi Mandate",
        "gst_verification": "Gst Verification",
        "documents": "Documents",
        "moratorium_details": "Moratorium Details",
        "colending_details": "Colending Details",
        "subvention": "Subvention",
    }
    
    target_mod = sheet_alias_map.get(s_norm)
    if target_mod:
        val = registry.get_validator(target_mod)
        if val:
            return val
            
    # Try direct registry lookup
    val = registry.get_validator(sheet_name)
    if val:
        return val
        
    val = registry.get_validator(sheet_name.replace("_", " "))
    if val:
        return val
        
    return None


def render_single_module_ui(selected_module_name, uploaded_file):
    validator = registry.get_validator(selected_module_name)
    if not validator:
        st.error(f"Selected module '{selected_module_name}' not found in registry.")
        return

    if uploaded_file is None:
        st.info("Please upload a source Excel file for this module from the left sidebar.")
        with st.expander("SynoFin Migration Audit Workflow", expanded=True):
            st.markdown("""
            ### Pre-Migration Data Audit Lifecycle:
            1. **Select Module**: Choose the target domain.
            2. **Upload Source Template**: Upload your source Excel template (`.xlsx` or `.xls`).
            3. **Execute Audit**: Validation rules run automatically on upload.
            4. **Remediate Findings**: Review plain-language remediation guidance for flagged records.
            5. **Export Audit Trail**: Download a multi-tab Excel validation audit report.
            """)
        return

    try:
        file_key = _uploaded_file_cache_key(uploaded_file)
        if file_key is None:
            raise ValueError("No file uploaded.")
        file_name, file_size, file_hash = file_key
        df = _read_excel_bytes_cached(file_name, file_size, file_hash, uploaded_file.getvalue())
    except Exception as exc:
        st.error(f"Failed to parse uploaded Excel file: {str(exc)}")
        return

    st.success(f"Source File Loaded: **{uploaded_file.name}** | **{len(df)}** Records | **{len(df.columns)}** Columns")

    with st.expander("Source Excel Raw Data Preview", expanded=False):
        st.dataframe(df.head(10), use_container_width=True)

    run_btn = st.button("Run Comprehensive Validation Audit", type="primary", use_container_width=True)

    cache_key = f"single_{uploaded_file.name}_{uploaded_file.size}_{selected_module_name}"
    if run_btn or st.session_state.get("active_cache_key") != cache_key:
        with st.spinner(f"Executing validation rules for '{selected_module_name}' module..."):
            results = validator.validate(df)
            summary = ValidationSummary.from_results(
                module=selected_module_name,
                total_records=len(df),
                rules_checked_count=len(validator.get_rules_metadata()) + len(validator.required_columns),
                results=results
            )
            impact_findings, loan_impact = LoanIdentificationEngine.analyze_impact(
                results, source_df=df, default_module=selected_module_name
            )
            st.session_state["validation_results"] = results
            st.session_state["validation_summary"] = summary
            st.session_state["impact_findings"] = impact_findings
            st.session_state["loan_impact"] = loan_impact
            st.session_state["active_cache_key"] = cache_key

    results = st.session_state.get("validation_results", [])
    summary = st.session_state.get("validation_summary")
    if not summary:
        return

    loan_impact = st.session_state.get("loan_impact")
    impact_findings = st.session_state.get("impact_findings")
    if loan_impact is None and results:
        impact_findings, loan_impact = LoanIdentificationEngine.analyze_impact(
            results, source_df=df, default_module=selected_module_name
        )
        st.session_state["loan_impact"] = loan_impact
        st.session_state["impact_findings"] = impact_findings

    st.markdown("---")

    tab_overview, tab_impact, tab_remediation, tab_inspector, tab_audit = st.tabs([
        "Executive Overview",
        "Affected Loans & Impact",
        "Remediation Guide",
        "Detailed Findings Inspector",
        "Audit Trail & Export"
    ])

    with tab_overview:
        st.subheader("Data Quality & Audit Metrics")
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("Total Records", summary.total_records)
        col2.metric("Rules Checked", summary.total_rules_checked)
        col3.metric("Passed Checks", summary.total_passed)
        col4.metric("Critical Errors", summary.total_errors, delta=f"-{summary.total_errors}" if summary.total_errors > 0 else "0", delta_color="inverse")
        col5.metric("Warnings", summary.total_warnings, delta=f"-{summary.total_warnings}" if summary.total_warnings > 0 else "0", delta_color="off")
        col6.metric("Affected Loans", loan_impact.total_unique_affected_loans if loan_impact else 0)

        if loan_impact:
            st.info(
                f"**Loan Identification Status:** "
                f"Resolved affected loans: **{loan_impact.resolved_affected_loans_count}** | "
                f"Unresolved findings: **{loan_impact.unresolved_findings_count}**"
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.write(f"**Migration Compliance Score:** `{summary.pass_percentage}%`")
        st.progress(summary.pass_percentage / 100.0)

        if summary.total_errors == 0 and summary.total_warnings == 0:
            st.success("Migration Status: **READY FOR IMPORT (Clean Data)**")
        elif summary.total_errors > 0:
            st.error("Migration Status: **ACTION REQUIRED BEFORE IMPORT (Critical Errors Found)**")
        else:
            st.warning("Migration Status: **ADVISORY WARNINGS DETECTED (Review Warnings)**")

    with tab_impact:
        st.subheader("Loan-Level Impact & Affected Loans Summary")
        if not loan_impact:
            st.info("No impact data available.")
        else:
            ic1, ic2, ic3, ic4 = st.columns(4)
            ic1.metric("Total Findings", loan_impact.total_findings)
            ic2.metric("Total Affected Rows", loan_impact.total_affected_rows)
            ic3.metric("Unique Affected Loans (Distinct)", loan_impact.total_unique_affected_loans)
            ic4.metric("Unique Failed Rules", loan_impact.unique_failed_rules_count)

            st.info(
                f"**Loan Identification Tracking:** "
                f"Resolved affected loans: **{loan_impact.resolved_affected_loans_count}** | "
                f"Unresolved findings: **{loan_impact.unresolved_findings_count}**"
            )

            st.markdown("---")
            st.markdown("### Rule-Wise Affected Loans Breakdown")
            if not loan_impact.rule_summaries:
                st.info("Clean validation run: no loans are affected by errors.")
            else:
                rule_table_data = []
                for rs in loan_impact.rule_summaries:
                    rule_table_data.append({
                        "Rule ID": rs.rule_id,
                        "Module": rs.module,
                        "Severity": rs.severity,
                        "Description": rs.description,
                        "Affected Rows": rs.affected_rows_count,
                        "Affected Loans": rs.affected_loans_count
                    })
                st.dataframe(pd.DataFrame(rule_table_data), use_container_width=True)

                st.markdown("#### Rule Drill-Down: View Affected Loans")
                for rs in loan_impact.rule_summaries:
                    details = loan_impact.loan_details_by_rule.get(rs.rule_id, [])
                    with st.expander(f"Rule {rs.rule_id}: View Affected Loans ({rs.affected_loans_count} loans, {rs.affected_rows_count} rows)"):
                        st.write(f"**Context:** {rs.description}")
                        st.write(f"**Severity:** `{rs.severity}` | **Module:** `{rs.module}`")
                        if details:
                            st.dataframe(pd.DataFrame(details), use_container_width=True)
                        else:
                            st.write("No loan details available for this rule.")

            st.markdown("---")
            st.markdown("### Loan-Level Drill-Down & Search")
            if not loan_impact.all_affected_loans:
                st.info("No affected loans found.")
            else:
                loans_df = pd.DataFrame(loan_impact.all_affected_loans)
                sc1, sc2 = st.columns(2)
                with sc1:
                    search_kw = st.text_input("Search Loan ID / Application Number", value="", placeholder="Type loan ID or application number...")
                with sc2:
                    all_rules = sorted(list(set(r.rule_id for r in loan_impact.rule_summaries)))
                    rule_filter = st.selectbox("Filter by Rule ID", options=["All Rules"] + all_rules)

                filtered_loans = loans_df.copy()
                if search_kw:
                    kw = search_kw.strip().lower()
                    filtered_loans = filtered_loans[
                        filtered_loans["Loan ID"].astype(str).str.lower().str.contains(kw, na=False) |
                        filtered_loans["Loan Application Number"].astype(str).str.lower().str.contains(kw, na=False)
                    ]
                if rule_filter != "All Rules":
                    filtered_loans = filtered_loans[filtered_loans["Rules Violated"].str.contains(rule_filter, na=False)]

                st.write(f"Displaying **{len(filtered_loans)}** of **{len(loans_df)}** unique affected loans:")
                st.dataframe(filtered_loans, use_container_width=True, height=350)

    with tab_remediation:
        st.subheader("Rule Violation Summary & Fix Guidance")
        if not results:
            st.info("Clean validation run: no rule violations detected.")
        else:
            results_df = pd.DataFrame([r.to_dict() for r in results])
            grouped_summary = (
                results_df.groupby(["Rule ID", "Field/Column", "Severity", "Description"])
                .agg(
                    Failed_Rows_Count=("Row Number", "count"),
                    Example_Actual_Value=("Actual Value", "first"),
                    Expected_Format=("Expected Value", "first")
                )
                .reset_index()
            )
            st.markdown(f"The audit engine flagged **{len(grouped_summary)}** distinct rule violation categories across your dataset:")
            for idx, row in grouped_summary.iterrows():
                sev_pill = '<span class="pill-error">CRITICAL ERROR</span>' if row["Severity"] == "ERROR" else '<span class="pill-warning">ADVISORY WARNING</span>'
                title_str = f"Column: {row['Field/Column']} | Rule: {row['Rule ID']} ({row['Failed_Rows_Count']} records affected)"
                with st.expander(title_str, expanded=(idx == 0)):
                    st.markdown(f"**Severity**: {sev_pill}", unsafe_allow_html=True)
                    st.write(f"**Rule Context:** {row['Description']}")
                    st.write(f"**Sample Found Value in Excel:** `{row['Example_Actual_Value']}`")
                    st.write(f"**Expected Format / Constraint:** `{row['Expected_Format']}`")
                    st.markdown(
                        f"""
                        <div class="fix-guidance-box">
                            <b>Recommended Excel Fix Action:</b><br>
                            Open <code>{uploaded_file.name}</code>, filter column <code>{row['Field/Column']}</code>, and update values to match <code>{row['Expected_Format']}</code>.
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    with tab_inspector:
        st.subheader("Record-Level Finding Inspector")
        if not results:
            st.info("No findings to display.")
        else:
            results_df = pd.DataFrame([r.to_dict() for r in results])
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                severity_filter = st.multiselect("Filter Severity", options=["ERROR", "WARNING"], default=["ERROR", "WARNING"])
            with f_col2:
                status_filter = st.multiselect("Filter Status", options=["FAIL", "PASS"], default=["FAIL"])
            with f_col3:
                field_options = ["All Fields"] + list(results_df["Field/Column"].unique())
                field_filter = st.selectbox("Filter Field / Column", options=field_options)

            filtered_df = results_df[
                (results_df["Severity"].isin(severity_filter)) &
                (results_df["Status"].isin(status_filter))
            ]
            if field_filter != "All Fields":
                filtered_df = filtered_df[filtered_df["Field/Column"] == field_filter]

            st.markdown(f"Displaying **{len(filtered_df)}** of **{len(results_df)}** audit findings:")
            st.dataframe(filtered_df, use_container_width=True, height=400)

    with tab_audit:
        st.subheader("Export & Audit Trail Metadata")
        st.markdown(
            f"""
            <div class="audit-box">
                <b>Migration Audit Run Details:</b><br>
                • Target System: SynoFin LMS Preprod (app_id=loan_management)<br>
                • Module: {selected_module_name}<br>
                • Source File: {uploaded_file.name}<br>
                • File Size: {uploaded_file.size / 1024:.2f} KB<br>
                • Total Rows Executed: {len(df)}<br>
                • Unique Affected Loans: {loan_impact.total_unique_affected_loans if loan_impact else 0}<br>
                • Audit Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                • Compliance Score: {summary.pass_percentage}%
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
        affected_loans_export_data = []
        if loan_impact:
            for r_summ in loan_impact.rule_summaries:
                for l_det in loan_impact.loan_details_by_rule.get(r_summ.rule_id, []):
                    affected_loans_export_data.append({
                        "Rule ID": r_summ.rule_id,
                        "Module": r_summ.module,
                        "Loan ID": l_det["Loan ID"],
                        "Loan Application Number": l_det["Loan Application Number"],
                        "Finding Count": l_det["Finding Count"],
                        "Error Rows": l_det["Error Rows"],
                        "Severity": r_summ.severity
                    })

        report_bytes = generate_excel_report(summary, results, affected_loans_data=affected_loans_export_data)
        file_name = f"SynoFin_Audit_Report_{selected_module_name}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        st.download_button(
            label="Download Official SynoFin Excel Audit Report (.xlsx)",
            data=report_bytes,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )

    st.session_state["active_audit_context"] = AuditContext(
        summary=summary,
        results=results,
        source_df=df,
        module_name=selected_module_name,
        loan_impact=loan_impact
    )


def render_data_cleaning_ui(uploaded_workbook):
    if uploaded_workbook is None:
        st.info("Upload an Excel workbook from the left sidebar to clean values across any sheet and column.")
        return

    workbook_key = (uploaded_workbook.name, uploaded_workbook.size)
    if (
        "cleaning_original_workbook" not in st.session_state
        or st.session_state.get("cleaning_workbook_key") != workbook_key
    ):
        try:
            file_key = _uploaded_file_cache_key(uploaded_workbook)
            if file_key is None:
                raise ValueError("No file uploaded.")
            file_name, file_size, file_hash = file_key
            original_workbook = _read_workbook_bytes_cached(file_name, file_size, file_hash, uploaded_workbook.getvalue())
        except Exception as exc:
            st.error(f"Failed to parse uploaded workbook for cleaning: {str(exc)}")
            return

        st.session_state["cleaning_original_workbook"] = original_workbook
        st.session_state["cleaning_workbook"] = {sheet: df.copy(deep=True) for sheet, df in original_workbook.items()}
        st.session_state["cleaning_workbook_key"] = workbook_key
        st.session_state["cleaning_summary"] = []
        st.session_state["cleaning_selected_columns"] = {}

    original_workbook = st.session_state["cleaning_original_workbook"]
    cleaned_workbook = st.session_state["cleaning_workbook"]
    sheet_names = list(cleaned_workbook.keys())

    st.subheader("Data Cleaning / Data Normalization")
    st.caption("Generic text normalization for any selected sheet and one or more columns. No business mappings or domain-specific transformations are applied.")

    if not sheet_names:
        st.warning("The uploaded workbook does not contain any usable sheets.")
        return

    selected_sheet = st.selectbox("Sheet", options=sheet_names, key="cleaning_sheet_selector")
    df = cleaned_workbook[selected_sheet]
    text_columns = get_text_columns(df)
    column_options = [col for col in df.columns if col is not None]
    if not column_options:
        st.warning("The selected sheet does not contain any columns to clean.")
        return

    selected_columns_state = st.session_state.setdefault("cleaning_selected_columns", {})
    selected_columns = selected_columns_state.get(selected_sheet, text_columns)
    selected_columns = [col for col in selected_columns if col in column_options]
    selected_columns_state[selected_sheet] = selected_columns

    st.markdown("### Multi-column selection")
    col_action1, col_action2 = st.columns(2)
    with col_action1:
        if st.button("Select All Text Columns", use_container_width=True):
            selected_columns_state[selected_sheet] = text_columns
            st.rerun()
    with col_action2:
        if st.button("Clear Selection", use_container_width=True):
            selected_columns_state[selected_sheet] = []
            st.rerun()

    selected_columns = st.multiselect(
        "Columns",
        options=column_options,
        default=selected_columns,
        key=f"cleaning_columns_{selected_sheet}",
    )
    selected_columns_state[selected_sheet] = selected_columns

    if not selected_columns:
        st.warning("Select at least one column to clean.")
        return

    single_operation = st.selectbox(
        "Operation",
        options=VALID_CLEANING_OPERATIONS,
        index=0,
        key="cleaning_single_operation",
    )

    preview_frames = []
    valid_selected_columns = []
    for column in selected_columns:
        if column not in df.columns:
            continue
        series = cleaned_workbook[selected_sheet][column]
        if not column_supports_text_cleaning(series):
            st.warning(f"Column '{column}' is numeric/date-like and is excluded from text cleaning operations.")
            continue
        valid_selected_columns.append(column)
        preview = preview_cleaning_changes(series, [single_operation], limit=100)
        if not preview.empty:
            preview = preview.assign(Column=column)
            preview_frames.append(preview[["Column", "Row", "Original", "Cleaned"]])

    st.markdown("### Preview of changes across selected columns")
    if not preview_frames:
        st.info("No text values require cleaning for the selected columns.")
    else:
        combined_preview = pd.concat(preview_frames, ignore_index=True)
        st.write(f"Total cells that will change: {len(combined_preview)}")
        st.dataframe(combined_preview.head(100), use_container_width=True)

    st.markdown("---")
    st.subheader("Cleaning Rules")
    rule_map = st.session_state.setdefault("cleaning_rule_map", {})
    current_rules = rule_map.setdefault(selected_sheet, {})
    for column in valid_selected_columns:
        current_rules[column] = st.selectbox(
            f"{column}",
            options=VALID_CLEANING_OPERATIONS,
            index=VALID_CLEANING_OPERATIONS.index(current_rules.get(column, single_operation)),
            key=f"cleaning_rule_{selected_sheet}_{column}",
        )

    col_bulk, col_rules = st.columns(2)
    with col_bulk:
        if st.button("Apply to Selected Columns", type="primary", use_container_width=True):
            updated_workbook = cleaned_workbook
            for column in valid_selected_columns:
                updated_workbook = apply_cleaning_to_workbook(
                    updated_workbook,
                    selected_sheet,
                    [column],
                    [single_operation],
                )
            st.session_state["cleaning_workbook"] = updated_workbook
            summary_rows = st.session_state.get("cleaning_summary", [])
            total_changes = sum(
                len(preview_cleaning_changes(cleaned_workbook[selected_sheet][column], [single_operation], limit=100))
                for column in valid_selected_columns
            )
            summary_rows.append({
                "Sheet": selected_sheet,
                "Columns Changed": len(valid_selected_columns),
                "Cells Changed": total_changes,
                "Operation": single_operation,
            })
            st.session_state["cleaning_summary"] = summary_rows
            st.success(f"Applied '{single_operation}' to {len(valid_selected_columns)} selected columns in '{selected_sheet}'.")
            st.rerun()

    with col_rules:
        if st.button("Apply All Cleaning Rules", use_container_width=True):
            updated_workbook = cleaned_workbook
            for column in valid_selected_columns:
                operation = current_rules.get(column, single_operation)
                updated_workbook = apply_cleaning_to_workbook(
                    updated_workbook,
                    selected_sheet,
                    [column],
                    [operation],
                )
            st.session_state["cleaning_workbook"] = updated_workbook
            summary_rows = st.session_state.get("cleaning_summary", [])
            total_changes = 0
            for column in valid_selected_columns:
                total_changes += len(preview_cleaning_changes(cleaned_workbook[selected_sheet][column], [current_rules.get(column, single_operation)], limit=100))
            summary_rows.append({
                "Sheet": selected_sheet,
                "Columns Changed": len(valid_selected_columns),
                "Cells Changed": total_changes,
                "Operation": " + ".join(f"{column}:{current_rules.get(column, single_operation)}" for column in valid_selected_columns),
            })
            st.session_state["cleaning_summary"] = summary_rows
            st.success(f"Applied all configured cleaning rules for '{selected_sheet}'.")
            st.rerun()

    with st.container():
        if st.button("Reset Changes", use_container_width=True):
            st.session_state["cleaning_workbook"] = {sheet: df.copy(deep=True) for sheet, df in original_workbook.items()}
            st.session_state["cleaning_summary"] = []
            st.success("Cleaned workbook reset to the original uploaded state.")
            st.rerun()

    st.markdown("---")
    st.subheader("Cleaning Summary")
    summary_rows = st.session_state.get("cleaning_summary", [])
    if summary_rows:
        summary_df = pd.DataFrame(summary_rows)
        grouped_summary = summary_df.groupby("Sheet", as_index=False).agg(
            Columns_Changed=("Columns Changed", "sum"),
            Cells_Changed=("Cells Changed", "sum")
        )
        st.dataframe(grouped_summary, use_container_width=True)
        st.write(f"Total Cells Changed: {int(grouped_summary['Cells_Changed'].sum())}")
    else:
        st.info("No cleaning operations have been applied yet.")

    st.markdown("---")
    cleaned_bytes = export_workbook_to_excel_bytes(st.session_state["cleaning_workbook"])
    st.download_button(
        label="Download Cleaned Excel",
        data=cleaned_bytes,
        file_name=f"{uploaded_workbook.name.rsplit('.', 1)[0]}_cleaned.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )

    with st.expander("Workbook preview (cleaned copy)", expanded=False):
        st.dataframe(st.session_state["cleaning_workbook"][selected_sheet].head(10), use_container_width=True)


def render_full_workbook_ui(uploaded_workbook):
    if uploaded_workbook is None:
        st.info("Upload your comprehensive master template file (e.g., `SynoFin_LMS_Migration_Template.xlsx`) from the left sidebar to audit all sheets in one click.")
        st.markdown("""
        ### Full Workbook Migration Audit Features:
        - **Automatic Sheet Decomposition**: Breaks the master Excel into all individual domain sheets.
        - **Target Domain Routing**: Automatically pairs each sheet (Loans, Customers, Disbursal, NACH, Charges, etc.) with its dedicated validator module.
        - **Consolidated Audit**: Generates a sheet-by-sheet health dashboard and a unified download report.
        """)
        return

    try:
        file_key = _uploaded_file_cache_key(uploaded_workbook)
        if file_key is None:
            raise ValueError("No file uploaded.")
        file_name, file_size, file_hash = file_key
        workbook_dict = _read_workbook_bytes_cached(file_name, file_size, file_hash, uploaded_workbook.getvalue())
        sheet_names = list(workbook_dict.keys())
    except Exception as exc:
        st.error(f"Failed to parse master Excel template: {str(exc)}")
        return
    skip_sheets = {"README", "CONTROL", "DATA DICTIONARY", "_lists"}
    auditable_sheets = [s for s in sheet_names if s not in skip_sheets]

    st.success(f"Master Workbook Loaded: **{uploaded_workbook.name}** | **{len(sheet_names)}** Total Sheets ({len(auditable_sheets)} auditable sheets detected)")

    run_full_btn = st.button("Audit Entire Master Workbook (All Sheets)", type="primary", use_container_width=True)

    cache_key = f"full_{uploaded_workbook.name}_{uploaded_workbook.size}"
    if run_full_btn or st.session_state.get("active_wb_cache_key") != cache_key:
        sheet_summaries = {}
        sheet_results = {}
        sheet_dfs = {}

        progress_bar = st.progress(0.0)
        status_text = st.empty()

        for idx, s in enumerate(auditable_sheets):
            status_text.text(f"Auditing sheet ({idx+1}/{len(auditable_sheets)}): '{s}'...")
            try:
                sheet_df = workbook_dict.get(s, pd.DataFrame())
            except Exception:
                sheet_df = pd.DataFrame()

            sheet_dfs[s] = sheet_df
            validator = get_validator_for_sheet(s)

            if validator and len(sheet_df) > 0:
                res = validator.validate(sheet_df)
                summ = ValidationSummary.from_results(
                    module=validator.module_name,
                    total_records=len(sheet_df),
                    rules_checked_count=len(validator.get_rules_metadata()) + len(validator.required_columns),
                    results=res
                )
            else:
                res = []
                summ = ValidationSummary(
                    module=validator.module_name if validator else s,
                    total_records=len(sheet_df),
                    total_rules_checked=0,
                    total_passed=0,
                    total_errors=0,
                    total_warnings=0,
                    pass_percentage=100.0 if len(sheet_df) == 0 else 0.0
                )

            sheet_results[s] = res
            sheet_summaries[s] = summ
            progress_bar.progress((idx + 1) / len(auditable_sheets))

        status_text.empty()
        progress_bar.empty()

        all_results_flat = []
        for res_list in sheet_results.values():
            all_results_flat.extend(res_list)
        wb_impact_findings, wb_loan_impact = LoanIdentificationEngine.analyze_impact(
            all_results_flat, workbook_dfs=sheet_dfs
        )

        st.session_state["wb_sheet_summaries"] = sheet_summaries
        st.session_state["wb_sheet_results"] = sheet_results
        st.session_state["wb_sheet_dfs"] = sheet_dfs
        st.session_state["wb_loan_impact"] = wb_loan_impact
        st.session_state["wb_impact_findings"] = wb_impact_findings
        st.session_state["active_wb_cache_key"] = cache_key

    sheet_summaries = st.session_state.get("wb_sheet_summaries", {})
    sheet_results = st.session_state.get("wb_sheet_results", {})
    sheet_dfs = st.session_state.get("wb_sheet_dfs", {})
    wb_loan_impact = st.session_state.get("wb_loan_impact")
    wb_impact_findings = st.session_state.get("wb_impact_findings")

    if not sheet_summaries:
        return

    if wb_loan_impact is None and sheet_results:
        all_results_flat = []
        for res_list in sheet_results.values():
            all_results_flat.extend(res_list)
        wb_impact_findings, wb_loan_impact = LoanIdentificationEngine.analyze_impact(
            all_results_flat, workbook_dfs=sheet_dfs
        )
        st.session_state["wb_loan_impact"] = wb_loan_impact
        st.session_state["wb_impact_findings"] = wb_impact_findings

    # Executive Overview Table across all sheets
    st.markdown("### Workbook Sheet-by-Sheet Health Matrix")
    
    matrix_data = []
    total_all_rows = 0
    total_all_errors = 0
    total_all_warnings = 0

    for s, summ in sheet_summaries.items():
        total_all_rows += summ.total_records
        total_all_errors += summ.total_errors
        total_all_warnings += summ.total_warnings

        if summ.total_errors == 0 and summ.total_warnings == 0:
            status_icon = "CLEAN"
        elif summ.total_errors > 0:
            status_icon = f"{summ.total_errors} ERRORS"
        else:
            status_icon = f"{summ.total_warnings} WARNINGS"

        matrix_data.append({
            "Sheet Name": s,
            "Target Module": summ.module,
            "Total Rows": summ.total_records,
            "Critical Errors": summ.total_errors,
            "Warnings": summ.total_warnings,
            "Compliance Score": f"{summ.pass_percentage:.1f}%",
            "Audit Status": status_icon
        })

    m_df = pd.DataFrame(matrix_data)
    st.dataframe(m_df, use_container_width=True, height=350)

    # Master Top Metrics
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Master Sheets", len(auditable_sheets))
    c2.metric("Total Records Audited", total_all_rows)
    c3.metric("Critical Errors", total_all_errors, delta=f"-{total_all_errors}" if total_all_errors > 0 else "0", delta_color="inverse")
    c4.metric("Total Warnings", total_all_warnings, delta=f"-{total_all_warnings}" if total_all_warnings > 0 else "0", delta_color="off")
    c5.metric("Affected Loans", wb_loan_impact.total_unique_affected_loans if wb_loan_impact else 0)
    c6.metric("Unresolved Findings", wb_loan_impact.unresolved_findings_count if wb_loan_impact else 0)

    if wb_loan_impact:
        st.info(
            f"**Master Loan Impact Status:** "
            f"Resolved affected loans: **{wb_loan_impact.resolved_affected_loans_count}** | "
            f"Unresolved findings: **{wb_loan_impact.unresolved_findings_count}**"
        )

    st.markdown("---")

    # Master Affected Loans & Impact Analysis Section
    if wb_loan_impact and wb_loan_impact.total_findings > 0:
        with st.expander("Master Affected Loans & Impact Analysis (All Sheets)", expanded=True):
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Total Findings", wb_loan_impact.total_findings)
            mc2.metric("Total Affected Rows", wb_loan_impact.total_affected_rows)
            mc3.metric("Unique Affected Loans (Distinct)", wb_loan_impact.total_unique_affected_loans)
            mc4.metric("Unique Failed Rules", wb_loan_impact.unique_failed_rules_count)

            st.markdown("#### Rule-Wise Affected Loans Breakdown")
            rule_table_data = []
            for rs in wb_loan_impact.rule_summaries:
                rule_table_data.append({
                    "Rule ID": rs.rule_id,
                    "Module": rs.module,
                    "Severity": rs.severity,
                    "Description": rs.description,
                    "Affected Rows": rs.affected_rows_count,
                    "Affected Loans": rs.affected_loans_count
                })
            st.dataframe(pd.DataFrame(rule_table_data), use_container_width=True)

            st.markdown("#### Rule Drill-Down: View Affected Loans")
            for rs in wb_loan_impact.rule_summaries[:15]:
                details = wb_loan_impact.loan_details_by_rule.get(rs.rule_id, [])
                with st.expander(f"Rule {rs.rule_id}: View Affected Loans ({rs.affected_loans_count} loans, {rs.affected_rows_count} rows)"):
                    st.write(f"**Context:** {rs.description}")
                    st.write(f"**Severity:** `{rs.severity}` | **Module:** `{rs.module}`")
                    if details:
                        st.dataframe(pd.DataFrame(details), use_container_width=True)

            st.markdown("#### Master Loan-Level Search & Filter")
            if wb_loan_impact.all_affected_loans:
                wb_loans_df = pd.DataFrame(wb_loan_impact.all_affected_loans)
                wsc1, wsc2, wsc3 = st.columns(3)
                with wsc1:
                    w_kw = st.text_input("Search Loan ID / Application Number", key="wb_search_kw", placeholder="Type loan ID or application number...")
                with wsc2:
                    wb_modules = ["All Modules"] + sorted(list(wb_loans_df["Module"].unique()))
                    w_mod = st.selectbox("Filter by Module", options=wb_modules, key="wb_mod_filter")
                with wsc3:
                    wb_rules = ["All Rules"] + sorted(list(set(r.rule_id for r in wb_loan_impact.rule_summaries)))
                    w_rule = st.selectbox("Filter by Rule ID", options=wb_rules, key="wb_rule_filter")

                filt_wb_df = wb_loans_df.copy()
                if w_kw:
                    kw_clean = w_kw.strip().lower()
                    filt_wb_df = filt_wb_df[
                        filt_wb_df["Loan ID"].astype(str).str.lower().str.contains(kw_clean, na=False) |
                        filt_wb_df["Loan Application Number"].astype(str).str.lower().str.contains(kw_clean, na=False)
                    ]
                if w_mod != "All Modules":
                    filt_wb_df = filt_wb_df[filt_wb_df["Module"] == w_mod]
                if w_rule != "All Rules":
                    filt_wb_df = filt_wb_df[filt_wb_df["Rules Violated"].str.contains(w_rule, na=False)]

                st.write(f"Displaying **{len(filt_wb_df)}** of **{len(wb_loans_df)}** unique affected loans:")
                st.dataframe(filt_wb_df, use_container_width=True, height=350)

        st.markdown("---")

    # Sheet Inspector Drill-Down
    st.markdown("### Individual Sheet Drill-Down Inspector")
    chosen_sheet = st.selectbox("Select Sheet to Inspect Findings", options=auditable_sheets)

    if chosen_sheet:
        res = sheet_results.get(chosen_sheet, [])
        summ = sheet_summaries.get(chosen_sheet)
        cur_df = sheet_dfs.get(chosen_sheet, pd.DataFrame())

        st.write(f"Sheet: **{chosen_sheet}** | Rows: **{len(cur_df)}** | Findings: **{len(res)}**")

        if not res:
            st.success(f"Sheet '{chosen_sheet}' is completely clean. No violations detected.")
        else:
            r_df = pd.DataFrame([r.to_dict() for r in res])
            st.dataframe(r_df, use_container_width=True, height=300)

    st.markdown("---")

    # Full Master Export Button
    st.markdown("### Download Consolidated Master Audit Report")
    st.write("Generates an Excel workbook with a **Master Summary Dashboard** tab, an **Affected Loans** tab, and individual audit tabs for each sheet.")

    wb_affected_loans_export_data = []
    if wb_loan_impact:
        for r_summ in wb_loan_impact.rule_summaries:
            for l_det in wb_loan_impact.loan_details_by_rule.get(r_summ.rule_id, []):
                wb_affected_loans_export_data.append({
                    "Rule ID": r_summ.rule_id,
                    "Module": r_summ.module,
                    "Loan ID": l_det["Loan ID"],
                    "Loan Application Number": l_det["Loan Application Number"],
                    "Finding Count": l_det["Finding Count"],
                    "Error Rows": l_det["Error Rows"],
                    "Severity": r_summ.severity
                })

    full_report_bytes = generate_multi_sheet_excel_report(
        sheet_summaries, sheet_results, affected_loans_data=wb_affected_loans_export_data
    )
    wb_filename = f"SynoFin_Master_Workbook_Audit_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    st.download_button(
        label="Download Master Consolidated Audit Report (.xlsx)",
        data=full_report_bytes,
        file_name=wb_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )

    st.session_state["active_audit_context"] = AuditContext(
        sheet_summaries=sheet_summaries,
        sheet_results=sheet_results,
        loan_impact=wb_loan_impact
    )


def main():
    # Sidebar Navigation & SynoFin Branding
    st.sidebar.markdown(
        """
        <div class="syno-sidebar-header">
            <div class="syno-sidebar-title">SynoFin LMS</div>
            <div class="syno-sidebar-sub">Loan Management Controls</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.sidebar.markdown("### Select Validation Mode")
    audit_mode = st.sidebar.radio(
        "Audit Mode",
        options=["Single Sheet / Module Upload", "Full Workbook Master Template (All Sheets)", "Data Cleaning"],
        index=0,
        help="Choose 'Single Sheet' for individual domain files, 'Full Workbook' for an entire migration template, or 'Data Cleaning' to normalize text values in a working copy."
    )

    st.sidebar.markdown("---")

    if audit_mode == "Data Cleaning":
        uploaded_workbook = st.sidebar.file_uploader(
            "Upload Workbook for Cleaning",
            type=["xlsx", "xls"],
            key="cleaning_file_uploader",
            help="Upload the workbook you want to clean without altering the original file."
        )
        render_data_cleaning_ui(uploaded_workbook)

    elif audit_mode == "Single Sheet / Module Upload":
        available_modules = registry.list_modules()
        if not available_modules:
            st.sidebar.error("No migration modules registered.")
            return

        selected_module_name = st.sidebar.selectbox(
            "Target Migration Module",
            options=available_modules,
            index=0,
            help="Select the migration domain corresponding to your source Excel file."
        )

        uploaded_file = st.sidebar.file_uploader(
            "Upload Source Excel File",
            type=["xlsx", "xls"],
            key="single_file_uploader",
            help="Supported formats: .xlsx, .xls (Max recommended file size 50MB)"
        )

        render_single_module_ui(selected_module_name, uploaded_file)

    else:
        st.sidebar.markdown("#### Upload Full Migration Template")
        uploaded_workbook = st.sidebar.file_uploader(
            "Upload Master Template Excel (.xlsx)",
            type=["xlsx", "xls"],
            key="full_wb_uploader",
            help="Upload full master file like SynoFin_LMS_Migration_Template.xlsx containing all 30+ sheets."
        )

        render_full_workbook_ui(uploaded_workbook)

    # Always render Floating Audit Assistant across both modes and startup
    cur_context = st.session_state.get("active_audit_context", None)
    render_floating_audit_assistant(cur_context)


if __name__ == "__main__":
    main()
