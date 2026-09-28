"""
Unit tests for Excel report generator.
"""

import io
from openpyxl import load_workbook
from src.core.models import ValidationResult, ValidationSummary, Severity, Status
from src.core.report_generator import generate_excel_report


def test_generate_excel_report_structure():
    results = [
        ValidationResult("R1", "Customer", "PAN", Severity.ERROR, Status.FAIL, "Invalid PAN", 2, "123", "ABCDE1234F"),
        ValidationResult("R2", "Customer", "DOB", Severity.WARNING, Status.FAIL, "Non-standard date", 3, "15/01/1990", "YYYY-MM-DD")
    ]
    summary = ValidationSummary.from_results("Customer", 5, 2, results)

    output = generate_excel_report(summary, results)
    assert isinstance(output, io.BytesIO)

    # Read generated workbook back
    wb = load_workbook(filename=output)
    sheet_names = wb.sheetnames

    assert "Summary Dashboard" in sheet_names
    assert "Validation Details" in sheet_names

    ws_details = wb["Validation Details"]
    assert ws_details.cell(row=1, column=1).value == "Rule ID"
    assert ws_details.cell(row=2, column=1).value == "R1"
    assert ws_details.cell(row=3, column=1).value == "R2"
