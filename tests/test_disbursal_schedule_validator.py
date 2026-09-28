"""
Unit tests for DisbursalScheduleValidator (DS-001 through DS-009).
"""

import pytest
import pandas as pd

import src.modules.disbursal_schedule.validator  # noqa: F401
from src.modules.disbursal_schedule.validator import DisbursalScheduleValidator
from src.core.models import Status


def make_df(**overrides):
    base = {
        "loan_application_number": "LN-001",
        "disbursal_number": 1,
        "disbursal_amount": 500000,
        "adjusted_amount": 5000,
        "net_disbursed_amount": 495000,
        "payment_date": "2024-01-15",
        "disbursal_status": "disbursed",
    }
    base.update(overrides)
    return pd.DataFrame([base])


def get_errors(df, rule_id=None):
    v = DisbursalScheduleValidator()
    results = v.validate(df)
    fails = [r for r in results if r.status == Status.FAIL]
    if rule_id:
        fails = [r for r in fails if r.rule_id == rule_id]
    return fails


def test_valid_row_passes():
    df = make_df()
    assert len(get_errors(df)) == 0


def test_ds_001_loan_application_number():
    df = make_df(loan_application_number=None)
    assert get_errors(df, "DS-001")


def test_ds_002_disbursal_number():
    assert get_errors(make_df(disbursal_number=None), "DS-002")
    assert get_errors(make_df(disbursal_number=0), "DS-002")
    assert get_errors(make_df(disbursal_number="invalid"), "DS-002")
    assert not get_errors(make_df(disbursal_number=2), "DS-002")


def test_ds_003_disbursal_amount():
    assert get_errors(make_df(disbursal_amount=None), "DS-003")
    assert get_errors(make_df(disbursal_amount=0), "DS-003")
    assert get_errors(make_df(disbursal_amount=-100), "DS-003")


def test_ds_004_adjusted_amount():
    assert get_errors(make_df(adjusted_amount=-50), "DS-004")
    # blank should be fine
    assert not get_errors(make_df(adjusted_amount=None, net_disbursed_amount=500000), "DS-004")


def test_ds_005_006_net_amount():
    assert get_errors(make_df(net_disbursed_amount=None), "DS-005")
    # Mismatch between disbursal_amount - adjusted_amount
    assert get_errors(make_df(disbursal_amount=500000, adjusted_amount=5000, net_disbursed_amount=400000), "DS-006")
    assert not get_errors(make_df(disbursal_amount=500000, adjusted_amount=5000, net_disbursed_amount=495000), "DS-006")


def test_ds_007_payment_date():
    assert get_errors(make_df(payment_date=None), "DS-007")
    assert get_errors(make_df(payment_date="invalid_date"), "DS-007")
    assert not get_errors(make_df(payment_date="2024-02-10"), "DS-007")


def test_ds_008_disbursal_status():
    assert get_errors(make_df(disbursal_status=None), "DS-008")
    assert get_errors(make_df(disbursal_status="invalid_status"), "DS-008")
    for s in ["disbursed", "partially_disbursed", "pending", "cancelled"]:
        assert not get_errors(make_df(disbursal_status=s), "DS-008")


def test_ds_009_duplicate_disbursal_number():
    row1 = make_df().iloc[0].to_dict()
    row2 = make_df().iloc[0].to_dict()
    df = pd.DataFrame([row1, row2])
    assert get_errors(df, "DS-009")

    # different disbursal number should pass
    row2["disbursal_number"] = 2
    df2 = pd.DataFrame([row1, row2])
    assert not get_errors(df2, "DS-009")
