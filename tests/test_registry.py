"""
Unit tests for ValidatorRegistry.
"""

from src.core.registry import ValidatorRegistry, registry
from src.modules.customer.validator import CustomerValidator


def test_registry_registration():
    reg = ValidatorRegistry()
    reg.register(CustomerValidator)
    
    assert reg.is_registered("Customer") is True
    assert reg.is_registered("customer") is True
    assert reg.is_registered("NON_EXISTENT") is False
    
    val = reg.get_validator("Customer")
    assert val is not None
    assert val.module_name == "Customer"


def test_global_registry_has_customer():
    assert "Customer" in registry.list_modules()
