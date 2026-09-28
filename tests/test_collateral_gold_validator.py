"""
Unit tests for CollateralGoldValidator.
"""
import pytest
import pandas as pd
import src.modules.collateral_gold.validator
from src.modules.collateral_gold.validator import CollateralGoldValidator
from src.core.models import Status

def test_basic_validation():
    v = CollateralGoldValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "coll_idx": "TEST", "collateral_type": "TEST", "collateral_status": "TEST", "collateral_number": "TEST", "market_value": "TEST", "is_primary_collateral": "TEST", "gold_packet_id": "TEST", "packet_no": "TEST", "ornament_count": "TEST", "total_gross_weight": "TEST", "total_net_weight": "TEST", "insurance_company": "TEST", "insurance_policy_no": "TEST", "insurance_end_date": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = CollateralGoldValidator()
    df = pd.DataFrame([{"loan_application_number": None, "coll_idx": None, "collateral_type": None, "collateral_status": None, "collateral_number": None, "market_value": None, "is_primary_collateral": None, "gold_packet_id": None, "packet_no": None, "ornament_count": None, "total_gross_weight": None, "total_net_weight": None, "insurance_company": None, "insurance_policy_no": None, "insurance_end_date": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
