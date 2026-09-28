import os

import pytest

from src.template_knowledge.service import TemplateKnowledgeService


WORKBOOK_PATH = r"C:\Users\satyam.raj_synoriq\Downloads\SynoFin_LMS_Migration_Template.xlsx"


@pytest.fixture(scope="module")
def knowledge_service():
    if not os.path.exists(WORKBOOK_PATH):
        pytest.skip("Workbook not found in Downloads.")
    return TemplateKnowledgeService(workbook_path=WORKBOOK_PATH)


def test_workbook_contains_expected_sheets(knowledge_service):
    sheet_names = knowledge_service.get_all_sheet_names()
    assert len(sheet_names) >= 30
    assert "README" in sheet_names
    assert "CONTROL" in sheet_names
    assert "DATA DICTIONARY" in sheet_names
    assert "loans" in sheet_names
    assert "repayment_schedule" in sheet_names


def test_data_dictionary_rows_are_represented(knowledge_service):
    data_dict = knowledge_service.get_data_dictionary()
    assert len(data_dict) > 300
    assert any(item.get("sheet") == "repayment_schedule" and item.get("column") == "status" for item in data_dict)


def test_exact_column_names_are_preserved(knowledge_service):
    item = knowledge_service.get_column_info("repayment_schedule", "status")
    assert item is not None
    assert item["column"] == "status"


def test_readme_knowledge_is_available(knowledge_service):
    readme = knowledge_service.get_readme_knowledge()
    assert "template purpose" in readme
    assert "linking key" in readme or "loan_application_number" in str(readme).lower()


def test_control_knowledge_is_available(knowledge_service):
    control = knowledge_service.get_control_knowledge()
    assert "batch control" in str(control).lower() or "reconciliation" in str(control).lower()


def test_lists_values_are_loaded(knowledge_service):
    allowed = knowledge_service.get_allowed_values_for_field("gender")
    assert allowed
    assert any(v.lower() == "male" for v in allowed)


def test_sample_rows_are_marked_as_sample_example(knowledge_service):
    sheet = knowledge_service.get_sheet_info("loans")
    assert sheet["sample_row"]
    assert sheet["sample_only"] is True


def test_get_column_info_works(knowledge_service):
    info = knowledge_service.get_column_info("customers", "customer_type")
    assert info is not None
    assert info["sheet"] == "customers"
    assert info["column"] == "customer_type"


def test_get_sheet_info_works(knowledge_service):
    info = knowledge_service.get_sheet_info("repayment_schedule")
    assert info is not None
    assert info["sheet_name"] == "repayment_schedule"


def test_get_allowed_values_works(knowledge_service):
    values = knowledge_service.get_allowed_values("repayment_schedule", "status")
    assert values is not None


def test_get_relationships_works(knowledge_service):
    rels = knowledge_service.get_relationships("nach_detail")
    assert rels
    assert any("loan_application_number" in str(r) for r in rels)


def test_search_template_knowledge_finds_known_terms(knowledge_service):
    hits = knowledge_service.search_template_knowledge("repayment_schedule status")
    assert hits
    assert any("status" in str(hit).lower() for hit in hits)

    hits2 = knowledge_service.search_template_knowledge("cust_idx")
    assert hits2

    hits3 = knowledge_service.search_template_knowledge("loan_application_number")
    assert hits3


def test_unknown_information_returns_not_defined_message(knowledge_service):
    result = knowledge_service.search_template_knowledge("totally_fake_template_field_zzz")
    assert result == ["Information is not defined in the migration template."] or result == []
