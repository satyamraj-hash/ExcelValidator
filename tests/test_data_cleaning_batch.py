import pandas as pd

from src.core.data_cleaning import (
    apply_cleaning_to_workbook,
    get_text_columns,
    reset_cleaning_workbook,
)


def test_multiple_columns_can_be_selected():
    df = pd.DataFrame({
        "first_name": ["Satyam", "Amit"],
        "middle_name": ["RAJ", ""],
        "amount": [100, 200],
        "dob": [pd.Timestamp("1990-01-01"), pd.Timestamp("1995-02-02")],
    })
    cols = get_text_columns(df)
    assert cols == ["first_name", "middle_name"]


def test_lowercase_applies_to_all_selected_text_columns():
    source = {
        "Customer": pd.DataFrame({
            "first_name": ["Satyam", "Amit"],
            "middle_name": ["RAJ", ""],
            "amount": [100, 200],
        })
    }
    cleaned = apply_cleaning_to_workbook(source, "Customer", ["first_name", "middle_name"], ["lowercase"])
    assert cleaned["Customer"]["first_name"].tolist() == ["satyam", "amit"]
    assert cleaned["Customer"]["middle_name"].tolist() == ["raj", None]
    assert cleaned["Customer"]["amount"].tolist() == [100, 200]


def test_select_all_text_columns_excludes_numeric_and_date_columns():
    df = pd.DataFrame({
        "name": ["Satyam", "Amit"],
        "city": ["Jaipur", "Delhi"],
        "amount": [10, 20],
        "dob": [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-02-01")],
    })
    assert get_text_columns(df) == ["name", "city"]


def test_multiple_operations_can_be_applied_without_downloading():
    source = {
        "Customer": pd.DataFrame({
            "first_name": ["  SATYAM  ", "Amit"],
            "address": ["Jaipur   Road", "  Delhi  "],
            "amount": [100, 200],
        })
    }
    cleaned = apply_cleaning_to_workbook(source, "Customer", ["first_name", "address"], ["trim", "remove_extra_spaces", "lowercase"])
    assert cleaned["Customer"]["first_name"].tolist() == ["satyam", "amit"]
    assert cleaned["Customer"]["address"].tolist() == ["jaipur road", "delhi"]
    assert cleaned["Customer"]["amount"].tolist() == [100, 200]


def test_changes_persist_across_multiple_cleaning_actions():
    source = {"Customer": pd.DataFrame({"first_name": ["SATYAM", "Amit"], "city": ["Jaipur", "Delhi"]})}
    cleaned = apply_cleaning_to_workbook(source, "Customer", ["first_name"], ["lowercase"])
    cleaned = apply_cleaning_to_workbook(cleaned, "Customer", ["city"], ["uppercase"])
    assert cleaned["Customer"]["first_name"].tolist() == ["satyam", "amit"]
    assert cleaned["Customer"]["city"].tolist() == ["JAIPUR", "DELHI"]


def test_final_workbook_contains_all_applied_changes():
    source = {"Customer": pd.DataFrame({"first_name": [" Satyam ", "Amit"], "city": [" Jaipur ", "Delhi"]})}
    cleaned = apply_cleaning_to_workbook(source, "Customer", ["first_name", "city"], ["trim", "lowercase"])
    assert cleaned["Customer"].to_dict("records") == [
        {"first_name": "satyam", "city": "jaipur"},
        {"first_name": "amit", "city": "delhi"},
    ]


def test_original_workbook_remains_unchanged():
    source = {"Customer": pd.DataFrame({"first_name": [" Satyam ", "Amit"], "city": [" Jaipur ", "Delhi"]})}
    cleaned = apply_cleaning_to_workbook(source, "Customer", ["first_name", "city"], ["trim", "lowercase"])
    assert source["Customer"]["first_name"].tolist() == [" Satyam ", "Amit"]
    assert source["Customer"]["city"].tolist() == [" Jaipur ", "Delhi"]
    assert cleaned["Customer"]["first_name"].tolist() == ["satyam", "amit"]


def test_reset_restores_original_data():
    source = {"Customer": pd.DataFrame({"first_name": [" Satyam ", "Amit"], "city": [" Jaipur ", "Delhi"]})}
    cleaned = apply_cleaning_to_workbook(source, "Customer", ["first_name", "city"], ["trim", "lowercase"])
    restored = reset_cleaning_workbook(cleaned, source)
    assert restored["Customer"].to_dict("records") == source["Customer"].to_dict("records")


def test_numeric_values_remain_unchanged():
    source = {"Customer": pd.DataFrame({"first_name": ["Satyam", "Amit"], "amount": [100, 200]})}
    cleaned = apply_cleaning_to_workbook(source, "Customer", ["first_name"], ["lowercase"])
    assert cleaned["Customer"]["amount"].tolist() == [100, 200]


def test_date_values_remain_unchanged():
    source = {"Customer": pd.DataFrame({"first_name": ["Satyam", "Amit"], "dob": [pd.Timestamp("1990-01-01"), pd.Timestamp("1995-02-02")]})}
    cleaned = apply_cleaning_to_workbook(source, "Customer", ["first_name"], ["lowercase"])
    assert cleaned["Customer"]["dob"].tolist() == [pd.Timestamp("1990-01-01"), pd.Timestamp("1995-02-02")]
