"""
Unit tests for CollateralPropertyValidator.
"""
import pytest
import pandas as pd
import src.modules.collateral_property.validator
from src.modules.collateral_property.validator import CollateralPropertyValidator
from src.core.models import Status

def test_basic_validation():
    v = CollateralPropertyValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "coll_idx": "TEST", "collateral_type": "TEST", "collateral_status": "TEST", "collateral_number": "TEST", "market_value": "TEST", "is_primary_collateral": "TEST", "property_status": "TEST", "nature_of_property": "TEST", "property_address_type": "TEST", "property_address_line_1": "TEST", "city": "TEST", "district": "TEST", "state": "TEST", "pincode": "TEST", "land_owner": "TEST", "land_area": "TEST", "land_area_unit": "TEST", "built_up_area_unit": "TEST", "is_building_constructed": "TEST", "ownership_type": "TEST", "registration_in_name_of": "TEST", "insurance_company": "TEST", "insurance_policy_no": "TEST", "insurance_end_date": "TEST", "asset_cost": "TEST", "repossession_status": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = CollateralPropertyValidator()
    df = pd.DataFrame([{"loan_application_number": None, "coll_idx": None, "collateral_type": None, "collateral_status": None, "collateral_number": None, "market_value": None, "is_primary_collateral": None, "property_status": None, "nature_of_property": None, "property_address_type": None, "property_address_line_1": None, "city": None, "district": None, "state": None, "pincode": None, "land_owner": None, "land_area": None, "land_area_unit": None, "built_up_area_unit": None, "is_building_constructed": None, "ownership_type": None, "registration_in_name_of": None, "insurance_company": None, "insurance_policy_no": None, "insurance_end_date": None, "asset_cost": None, "repossession_status": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
