"""
Knowledge Layer for SynoFin Migration Rules.

Extracts live rule metadata and mandatory columns from all registered modules
in ValidatorRegistry. Acts as the single source-of-truth for the assistant.
"""

import importlib
import pkgutil
from typing import Dict, List, Optional, Any
from src.core.registry import registry
from src.core.base import ValidationRule, BaseValidator
import src.modules


def ensure_all_modules_registered():
    """Dynamically loads and registers all validator modules under src.modules."""
    if len(registry.list_modules()) < 10:
        for _, module_name, is_pkg in pkgutil.iter_modules(src.modules.__path__):
            if is_pkg:
                try:
                    importlib.import_module(f"src.modules.{module_name}.validator")
                except ImportError:
                    pass


class RuleKnowledgeBase:
    """Dynamic, read-only rule knowledge base using ValidatorRegistry."""

    @classmethod
    def list_all_modules(cls) -> List[str]:
        ensure_all_modules_registered()
        return sorted(registry.list_modules())

    @classmethod
    def get_module_validator(cls, module_name: str) -> Optional[BaseValidator]:
        ensure_all_modules_registered()
        return registry.get_validator(module_name)

    @classmethod
    def get_module_rules(cls, module_name: str) -> List[ValidationRule]:
        v = cls.get_module_validator(module_name)
        if not v:
            return []
        return v.get_rules_metadata()

    @classmethod
    def get_module_required_columns(cls, module_name: str) -> List[str]:
        v = cls.get_module_validator(module_name)
        if not v:
            return []
        return v.required_columns

    @classmethod
    def find_rule(cls, rule_id: str) -> Optional[Dict[str, Any]]:
        """Search all registered modules for a given rule_id (case-insensitive)."""
        ensure_all_modules_registered()
        target_id = rule_id.strip().upper().replace("_", "-")
        for mod in registry.list_modules():
            v = registry.get_validator(mod)
            if not v:
                continue
            for r in v.get_rules_metadata():
                norm_rid = r.rule_id.strip().upper().replace("_", "-")
                if norm_rid == target_id:
                    return {
                        "rule_id": r.rule_id,
                        "module": r.module,
                        "field": r.field,
                        "description": r.description,
                        "severity": r.severity.value if hasattr(r.severity, "value") else str(r.severity),
                    }
        return None

    @classmethod
    def search_rules_by_keyword(cls, keyword: str) -> List[Dict[str, Any]]:
        """Search rules across all modules matching a keyword in field or description."""
        ensure_all_modules_registered()
        kw = keyword.lower().strip()
        matches = []
        for mod in registry.list_modules():
            v = registry.get_validator(mod)
            if not v:
                continue
            for r in v.get_rules_metadata():
                if kw in r.field.lower() or kw in r.description.lower() or kw in r.rule_id.lower():
                    matches.append({
                        "rule_id": r.rule_id,
                        "module": r.module,
                        "field": r.field,
                        "description": r.description,
                        "severity": r.severity.value if hasattr(r.severity, "value") else str(r.severity),
                    })
        return matches
