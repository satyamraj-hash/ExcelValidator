"""
Unit tests for CollateralVehicleValidator.
"""
import pytest
import pandas as pd
import src.modules.collateral_vehicle.validator
from src.modules.collateral_vehicle.validator import CollateralVehicleValidator
from src.core.models import Status

def test_basic_validation():
    v = CollateralVehicleValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "coll_idx": "TEST", "collateral_type": "TEST", "collateral_status": "TEST", "collateral_number": "TEST", "market_value": "TEST", "is_primary_collateral": "TEST", "vehicle_type": "TEST", "vehicle_rc_no": "TEST", "manufacturer": "TEST", "model": "TEST", "chassis_no": "TEST", "engine_no": "TEST", "fuel_type": "TEST", "year_of_registration": "TEST", "registration_in_name_of": "TEST", "on_road_price": "TEST", "se_price": "TEST", "dealer_price": "TEST", "asset_cost": "TEST", "asset_type": "TEST", "insurance_company": "TEST", "insurance_policy_no": "TEST", "insurance_end_date": "TEST", "repossession_status": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = CollateralVehicleValidator()
    df = pd.DataFrame([{"loan_application_number": None, "coll_idx": None, "collateral_type": None, "collateral_status": None, "collateral_number": None, "market_value": None, "is_primary_collateral": None, "vehicle_type": None, "vehicle_rc_no": None, "manufacturer": None, "model": None, "chassis_no": None, "engine_no": None, "fuel_type": None, "year_of_registration": None, "registration_in_name_of": None, "on_road_price": None, "se_price": None, "dealer_price": None, "asset_cost": None, "asset_type": None, "insurance_company": None, "insurance_policy_no": None, "insurance_end_date": None, "repossession_status": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
