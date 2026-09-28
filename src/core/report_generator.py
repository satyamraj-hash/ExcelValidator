"""
Excel Validation Report Generator using OpenPyXL.
"""

from datetime import datetime
import io
from typing import List, Optional, Dict, Any
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from src.core.models import ValidationResult, ValidationSummary, Severity, Status


def _add_affected_loans_sheet(
    wb: Workbook,
    affected_loans_data: Optional[List[Dict[str, Any]]],
    border_all: Border,
    fill_navy: PatternFill,
    fill_light_gray: PatternFill,
    font_header: Font,
    font_regular: Font,
    align_center: Alignment,
    align_left: Alignment
):
    """Adds the Affected Loans tab to an Excel workbook."""
    if not affected_loans_data:
        return

    ws_loans = wb.create_sheet(title="Affected Loans")
    ws_loans.views.sheetView[0].showGridLines = True

    # Title
    ws_loans["A1"] = "Affected Loans Summary"
    ws_loans["A1"].font = Font(name="Calibri", size=15, bold=True, color="1B365D")
    ws_loans["A2"] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ws_loans["A2"].font = Font(name="Calibri", size=10, italic=True, color="555555")

    headers = [
        "Rule ID", "Module", "Loan ID", "Loan Application Number",
        "Finding Count", "Error Rows", "Severity"
    ]

    for col_idx, h in enumerate(headers, 1):
        c = ws_loans.cell(row=4, column=col_idx, value=h)
        c.font = font_header
        c.fill = fill_navy
        c.alignment = align_center
        c.border = border_all

    cur_r = 5
    for item in affected_loans_data:
        vals = [
            item.get("Rule ID", "N/A"),
            item.get("Module", "N/A"),
            item.get("Loan ID", "Unresolved"),
            item.get("Loan Application Number", "Unresolved"),
            item.get("Finding Count", 1),
            item.get("Error Rows", "N/A"),
            item.get("Severity", "ERROR")
        ]
        for c_idx, val in enumerate(vals, 1):
            cell = ws_loans.cell(row=cur_r, column=c_idx, value=val)
            cell.font = font_regular
            cell.border = border_all
            cell.alignment = align_center if c_idx in [1, 5, 7] else align_left
        cur_r += 1

    for col in ws_loans.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_loans.column_dimensions[col_letter].width = min(max(max_len + 3, 14), 45)


def generate_excel_report(
    summary: ValidationSummary,
    results: List[ValidationResult],
    affected_loans_data: Optional[List[Dict[str, Any]]] = None
) -> io.BytesIO:
    """
    Generate a professional, styled Excel validation report with:
    - Tab 1: Summary Dashboard
    - Tab 2: Detailed Validation Results
    - Tab 3: Affected Loans (optional/enhanced)
    
    Returns in-memory BytesIO buffer ready for Streamlit download.
    """
    wb = Workbook()
    
    # ----------------------------------------------------
    # Styling Definitions
    # ----------------------------------------------------
    font_title = Font(name="Calibri", size=16, bold=True, color="1B365D")
    font_subtitle = Font(name="Calibri", size=11, italic=True, color="555555")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=11, bold=True)
    font_regular = Font(name="Calibri", size=11)
    
    fill_navy = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    fill_light_gray = PatternFill(start_color="F2F4F4", end_color="F2F4F4", fill_type="solid")
    
    fill_error = PatternFill(start_color="FADBD8", end_color="FADBD8", fill_type="solid")     # Light Red
    fill_warning = PatternFill(start_color="FCF3CF", end_color="FCF3CF", fill_type="solid")   # Light Yellow
    fill_pass = PatternFill(start_color="D4EFDF", end_color="D4EFDF", fill_type="solid")      # Light Green

    thin_border_side = Side(border_style="thin", color="CCCCCC")
    border_all = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")

    # ----------------------------------------------------
    # TAB 1: Summary Dashboard
    # ----------------------------------------------------
    ws_summary = wb.active
    ws_summary.title = "Summary Dashboard"
    ws_summary.views.sheetView[0].showGridLines = True

    # Title Block
    ws_summary["A1"] = "Excel Migration Validation Summary"
    ws_summary["A1"].font = font_title
    ws_summary["A2"] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ws_summary["A2"].font = font_subtitle

    # Metadata Block
    metadata_rows = [
        ("Target System:", "SynoFin LMS (app_id=loan_management)"),
        ("Migration Module:", summary.module),
        ("Total Records Evaluated:", summary.total_records),
        ("Total Rules Checked:", summary.total_rules_checked),
        ("Passed Evaluations:", summary.total_passed),
        ("Critical Errors:", summary.total_errors),
        ("Advisory Warnings:", summary.total_warnings),
        ("Compliance Score:", f"{summary.pass_percentage:.2f}%")
    ]

    for idx, (label, val) in enumerate(metadata_rows, start=4):
        c_label = ws_summary.cell(row=idx, column=1, value=label)
        c_label.font = font_bold
        c_label.border = border_all
        c_label.fill = fill_light_gray

        c_val = ws_summary.cell(row=idx, column=2, value=val)
        c_val.font = font_regular
        c_val.border = border_all

    # Auto-fit columns for Summary
    ws_summary.column_dimensions["A"].width = 28
    ws_summary.column_dimensions["B"].width = 45

    # ----------------------------------------------------
    # TAB 2: Detailed Validation Results
    # ----------------------------------------------------
    ws_details = wb.create_sheet(title="Validation Details")
    ws_details.views.sheetView[0].showGridLines = True

    headers = [
        "Rule ID", "Module", "Field/Column", "Severity", "Status",
        "Description", "Row Number", "Actual Value", "Expected Value"
    ]

    for col_idx, h in enumerate(headers, 1):
        cell = ws_details.cell(row=1, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = border_all

    # Write detail rows
    for row_idx, result in enumerate(results, start=2):
        row_data = result.to_dict()
        ws_details.append([
            row_data["Rule ID"],
            row_data["Module"],
            row_data["Field/Column"],
            row_data["Severity"],
            row_data["Status"],
            row_data["Description"],
            row_data["Row Number"],
            row_data["Actual Value"],
            row_data["Expected Value"]
        ])

        # Formatting row
        sev_cell = ws_details.cell(row=row_idx, column=4)
        status_cell = ws_details.cell(row=row_idx, column=5)

        for col_num in range(1, len(headers) + 1):
            c = ws_details.cell(row=row_idx, column=col_num)
            c.font = font_regular
            c.border = border_all

        if row_data["Status"] == "PASS":
            status_cell.fill = fill_pass
        else:
            if row_data["Severity"] == "ERROR":
                sev_cell.fill = fill_error
                status_cell.fill = fill_error
            elif row_data["Severity"] == "WARNING":
                sev_cell.fill = fill_warning
                status_cell.fill = fill_warning

    # Auto-fit columns for Details
    for col in ws_details.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_details.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 50)

    # ----------------------------------------------------
    # TAB 3: Affected Loans (if available)
    # ----------------------------------------------------
    if affected_loans_data:
        _add_affected_loans_sheet(
            wb=wb,
            affected_loans_data=affected_loans_data,
            border_all=border_all,
            fill_navy=fill_navy,
            fill_light_gray=fill_light_gray,
            font_header=font_header,
            font_regular=font_regular,
            align_center=align_center,
            align_left=align_left
        )

    # Save to BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def generate_multi_sheet_excel_report(
    sheet_summaries: dict,
    all_results: dict,
    affected_loans_data: Optional[List[Dict[str, Any]]] = None
) -> io.BytesIO:
    """
    Generate an Excel validation report containing an Overall Summary sheet,
    detailed finding sheets for every sheet audited, and an Affected Loans tab.
    """
    wb = Workbook()
    
    font_title = Font(name="Calibri", size=15, bold=True, color="1B365D")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=11, bold=True)
    font_regular = Font(name="Calibri", size=11)
    
    fill_navy = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    fill_light_gray = PatternFill(start_color="F2F4F4", end_color="F2F4F4", fill_type="solid")
    fill_error = PatternFill(start_color="FADBD8", end_color="FADBD8", fill_type="solid")
    fill_warning = PatternFill(start_color="FCF3CF", end_color="FCF3CF", fill_type="solid")
    fill_pass = PatternFill(start_color="D4EFDF", end_color="D4EFDF", fill_type="solid")
    
    thin_side = Side(border_style="thin", color="CCCCCC")
    border_all = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    
    # 1. Master Summary Sheet
    ws_master = wb.active
    ws_master.title = "Master Summary"
    ws_master.views.sheetView[0].showGridLines = True
    
    ws_master["A1"] = "SynoFin Migration Workbook Validation Summary"
    ws_master["A1"].font = font_title
    ws_master["A2"] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ws_master["A2"].font = Font(name="Calibri", size=10, italic=True, color="555555")
    
    headers = ["Sheet Name", "Module", "Total Rows", "Errors", "Warnings", "Compliance %", "Audit Status"]
    for col_idx, h in enumerate(headers, 1):
        c = ws_master.cell(row=4, column=col_idx, value=h)
        c.font = font_header
        c.fill = fill_navy
        c.alignment = align_center
        c.border = border_all
        
    r_idx = 5
    for sheet_name, summ in sheet_summaries.items():
        status_text = "CLEAN" if summ.total_errors == 0 and summ.total_warnings == 0 else ("FAIL" if summ.total_errors > 0 else "WARNING")
        row_vals = [
            sheet_name,
            summ.module,
            summ.total_records,
            summ.total_errors,
            summ.total_warnings,
            f"{summ.pass_percentage:.1f}%",
            status_text
        ]
        for c_idx, val in enumerate(row_vals, 1):
            cell = ws_master.cell(row=r_idx, column=c_idx, value=val)
            cell.font = font_regular
            cell.border = border_all
            cell.alignment = align_center if c_idx > 2 else align_left
            if c_idx == 4 and summ.total_errors > 0:
                cell.fill = fill_error
            elif c_idx == 5 and summ.total_warnings > 0:
                cell.fill = fill_warning
            elif c_idx == 7:
                cell.fill = fill_pass if status_text == "CLEAN" else (fill_error if status_text == "FAIL" else fill_warning)
        r_idx += 1
        
    for col in ws_master.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_master.column_dimensions[col_letter].width = max(max_len + 3, 14)

    # 2. Affected Loans Tab (if available)
    if affected_loans_data:
        _add_affected_loans_sheet(
            wb=wb,
            affected_loans_data=affected_loans_data,
            border_all=border_all,
            fill_navy=fill_navy,
            fill_light_gray=fill_light_gray,
            font_header=font_header,
            font_regular=font_regular,
            align_center=align_center,
            align_left=align_left
        )
        
    # 3. Detailed Findings Sheets (One sheet per audited template sheet)
    detail_headers = ["Rule ID", "Field/Column", "Severity", "Status", "Description", "Row", "Actual Value", "Expected Value"]
    for sheet_name, results in all_results.items():
        if not results:
            continue
        tab_title = f"{sheet_name[:28]}"
        ws_sheet = wb.create_sheet(title=tab_title)
        ws_sheet.views.sheetView[0].showGridLines = True
        
        ws_sheet["A1"] = f"Findings: {sheet_name}"
        ws_sheet["A1"].font = font_title
        
        for c_idx, h in enumerate(detail_headers, 1):
            c = ws_sheet.cell(row=3, column=c_idx, value=h)
            c.font = font_header
            c.fill = fill_navy
            c.alignment = align_center
            c.border = border_all
            
        cur_r = 4
        for res in results:
            d = res.to_dict()
            vals = [
                d.get("Rule ID"),
                d.get("Field/Column"),
                d.get("Severity"),
                d.get("Status"),
                d.get("Description"),
                d.get("Row Number"),
                str(d.get("Actual Value", "")),
                str(d.get("Expected Value", ""))
            ]
            for c_idx, val in enumerate(vals, 1):
                cell = ws_sheet.cell(row=cur_r, column=c_idx, value=val)
                cell.font = font_regular
                cell.border = border_all
                if c_idx == 3:
                    cell.fill = fill_error if val == "ERROR" else fill_warning
                elif c_idx == 4:
                    cell.fill = fill_pass if val == "PASS" else fill_error
            cur_r += 1
            
        for col in ws_sheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws_sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 40)
            
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
