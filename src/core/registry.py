"""
Dynamic Registry for Excel Migration Module Validators.
"""

from typing import Dict, List, Type, Optional
from src.core.base import BaseValidator


class ValidatorRegistry:
    """
    Registry for managing and fetching available migration module validators.
    Enables adding future modules (Loan Application, Repayment Schedule, etc.)
    without modifying core application code.
    """

    def __init__(self):
        self._validators: Dict[str, BaseValidator] = {}

    def register(self, validator_cls: Type[BaseValidator]) -> None:
        """Register a validator class instance."""
        instance = validator_cls()
        module_key = instance.module_name.lower().strip()
        self._validators[module_key] = instance

    def get_validator(self, module_name: str) -> Optional[BaseValidator]:
        """Fetch validator instance by module name (case-insensitive)."""
        key = module_name.lower().strip()
        return self._validators.get(key)

    def list_modules(self) -> List[str]:
        """Return list of registered module display names."""
        return [v.module_name for v in self._validators.values()]

    def is_registered(self, module_name: str) -> bool:
        """Check if module is registered."""
        return module_name.lower().strip() in self._validators


# Global registry singleton instance
registry = ValidatorRegistry()
