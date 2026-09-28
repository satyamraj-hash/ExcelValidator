"""
Unit tests for ExpenseInformationValidator.
"""
import pytest
import pandas as pd
import src.modules.expense_information.validator
from src.modules.expense_information.validator import ExpenseInformationValidator
from src.core.models import Status

def test_basic_validation():
    v = ExpenseInformationValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "cust_idx": "TEST", "expense_idx": "TEST", "source": "TEST", "expenseAmount": "TEST", "incomeFrequency": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = ExpenseInformationValidator()
    df = pd.DataFrame([{"loan_application_number": None, "cust_idx": None, "expense_idx": None, "source": None, "expenseAmount": None, "incomeFrequency": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
