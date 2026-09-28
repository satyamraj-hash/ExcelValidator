import pandas as pd

from src.core.data_cleaning import (
    apply_cleaning_to_series,
    preview_cleaning_changes,
    apply_cleaning_to_workbook,
    reset_cleaning_workbook,
    normalize_text,
)


def test_lowercase():
    series = pd.Series(["Paid", "PAID", " paid "])
    cleaned = apply_cleaning_to_series(series, ["lowercase"])
    assert cleaned.tolist() == ["paid", "paid", "paid"]


def test_uppercase():
    series = pd.Series(["paid", "Pending"])
    cleaned = apply_cleaning_to_series(series, ["uppercase"])
    assert cleaned.tolist() == ["PAID", "PENDING"]


def test_trim():
    series = pd.Series(["  Paid  ", "Paid  "])
    cleaned = apply_cleaning_to_series(series, ["trim"])
    assert cleaned.tolist() == ["Paid", "Paid"]


def test_extra_spaces():
    series = pd.Series(["Paid    Amount", "  EMI    Payment  "])
    cleaned = apply_cleaning_to_series(series, ["remove_extra_spaces"])
    assert cleaned.tolist() == ["Paid Amount", "EMI Payment"]


def test_line_break_removal():
    series = pd.Series(["EMI\nPayment", "Paid\r\nNow"])
    cleaned = apply_cleaning_to_series(series, ["remove_line_breaks"])
    assert cleaned.tolist() == ["EMI Payment", "Paid Now"]


def test_combined_operations():
    series = pd.Series(["  EMI   PAYMENT  "])
    cleaned = apply_cleaning_to_series(series, ["trim", "remove_extra_spaces", "lowercase"])
    assert cleaned.tolist() == ["emi payment"]


def test_numeric_values_remain_unchanged():
    series = pd.Series([1000, 2500.5])
    cleaned = apply_cleaning_to_series(series, ["lowercase"])
    assert cleaned.tolist() == [1000, 2500.5]


def test_date_values_remain_unchanged():
    series = pd.Series([pd.Timestamp("2024-01-01"), "2024-01-02"])  # second value is a string
    cleaned = apply_cleaning_to_series(series, ["uppercase"])
    assert cleaned.iloc[0] == pd.Timestamp("2024-01-01")
    assert cleaned.iloc[1] == "2024-01-02"


def test_blank_values_are_handled_safely():
    series = pd.Series([None, "  ", "Paid", ""]) 
    cleaned = apply_cleaning_to_series(series, ["trim", "lowercase"])
    assert cleaned.tolist() == [None, None, "paid", None]


def test_only_selected_column_changes():
    df = pd.DataFrame({
        "status": ["Paid", "PENDING"],
        "amount": [100, 200],
    })
    workbook = {"Sheet1": df}
    result = apply_cleaning_to_workbook(workbook, "Sheet1", "status", ["lowercase"])
    assert result["Sheet1"]["status"].tolist() == ["paid", "pending"]
    assert result["Sheet1"]["amount"].tolist() == [100, 200]


def test_other_sheets_remain_unchanged():
    wb = {
        "SheetA": pd.DataFrame({"status": ["Paid"]}),
        "SheetB": pd.DataFrame({"status": ["PAID"]}),
    }
    result = apply_cleaning_to_workbook(wb, "SheetA", "status", ["lowercase"])
    assert result["SheetA"]["status"].tolist() == ["paid"]
    assert result["SheetB"]["status"].tolist() == ["PAID"]


def test_original_workbook_remains_unchanged():
    source = {"Sheet1": pd.DataFrame({"status": ["Paid", "PAID"]})}
    cleaned = apply_cleaning_to_workbook(source, "Sheet1", "status", ["lowercase"])
    assert source["Sheet1"]["status"].tolist() == ["Paid", "PAID"]
    assert cleaned["Sheet1"]["status"].tolist() == ["paid", "paid"]


def test_multiple_operations_can_be_applied_sequentially():
    series = pd.Series(["  EMI   PAYMENT  "], dtype="object")
    cleaned = apply_cleaning_to_series(series, ["trim", "remove_extra_spaces", "lowercase"])
    assert cleaned.tolist() == ["emi payment"]
    cleaned2 = apply_cleaning_to_series(cleaned, ["uppercase"])
    assert cleaned2.tolist() == ["EMI PAYMENT"]


def test_normalize_text_handles_nulls_and_strings():
    assert normalize_text("  PAID  ", ["trim", "lowercase"]) == "paid"
    assert normalize_text(None, ["trim", "lowercase"]) is None
    assert normalize_text(123, ["lowercase"]) == 123


def test_preview_shows_only_rows_that_change():
    series = pd.Series(["Paid", "PAID", "Pending", "  clean  "])
    preview = preview_cleaning_changes(series, ["lowercase"])
    assert len(preview) == 4
    assert preview["Original"].tolist() == ["Paid", "PAID", "Pending", "  clean  "]
    assert preview["Cleaned"].tolist() == ["paid", "paid", "pending", "clean"]


def test_reset_restores_original_data():
    original = {"Sheet1": pd.DataFrame({"status": ["Paid", "PAID"]})}
    cleaned = apply_cleaning_to_workbook(original, "Sheet1", "status", ["lowercase"])
    restored = reset_cleaning_workbook(cleaned, original)
    assert restored["Sheet1"]["status"].tolist() == ["Paid", "PAID"]
