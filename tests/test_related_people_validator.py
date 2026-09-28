"""
Unit tests for RelatedPeopleValidator.
"""
import pytest
import pandas as pd
import src.modules.related_people.validator
from src.modules.related_people.validator import RelatedPeopleValidator
from src.core.models import Status

def test_basic_validation():
    v = RelatedPeopleValidator()
    df = pd.DataFrame([{"loan_application_number": "TEST", "cust_idx": "TEST", "rel_idx": "TEST", "people_type": "TEST", "relation_type": "TEST", "name": "TEST", "gender": "TEST", "dob": "TEST", "pan": "TEST", "aadhaar": "TEST", "income": "TEST", "current_address": "TEST", "current_city": "TEST", "current_district": "TEST", "current_state": "TEST", "current_landmark": "TEST", "current_address_type": "TEST", "permanent_address": "TEST", "permanent_city": "TEST", "permanent_district": "TEST", "permanent_state": "TEST", "permanent_landmark": "TEST", "permanent_address_type": "TEST", "remarks": "TEST"}])
    results = v.validate(df)
    assert not any(r.status == Status.FAIL for r in results)

def test_missing_mandatory():
    v = RelatedPeopleValidator()
    df = pd.DataFrame([{"loan_application_number": None, "cust_idx": None, "rel_idx": None, "people_type": None, "relation_type": None, "name": None, "gender": None, "dob": None, "pan": None, "aadhaar": None, "income": None, "current_address": None, "current_city": None, "current_district": None, "current_state": None, "current_landmark": None, "current_address_type": None, "permanent_address": None, "permanent_city": None, "permanent_district": None, "permanent_state": None, "permanent_landmark": None, "permanent_address_type": None, "remarks": None}])
    results = v.validate(df)
    assert any(r.status == Status.FAIL for r in results)
