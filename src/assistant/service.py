"""
SynoFin Migration Audit Assistant Service.

Handles:
- Natural Hindi/Hinglish & English conversations
- General Fintech, LMS, Banking and Migration concepts
- Inquiries about validation rules across all 30 modules
- Exact audit statistics, summaries, and error breakdowns
- Entity lookups (loan IDs, customer IDs)
- Smart conversational context & follow-ups
"""

import os
import re
from typing import Dict, List, Any, Optional
import pandas as pd

from src.core.models import ValidationResult, ValidationSummary, Severity, Status
from src.core.loan_impact import LoanIdentificationEngine
from src.assistant.knowledge import RuleKnowledgeBase
from src.assistant.fintech_knowledge import lookup_fintech_concept
from src.assistant.gemini_agent import GeminiAgent
from src.template_knowledge.service import TemplateKnowledgeService

FALLBACK_MESSAGE = "I couldn't match that to a specific audit finding or rule in the current context."
UNKNOWN_INTENT_MESSAGE = "I couldn't determine which migration information you're asking about. You can ask me about sheets, columns, validation rules, audit findings, or specific loans."

DEFAULT_HELP_MESSAGE = (
    "I am your **SynoFin LMS Migration Audit & Fintech Assistant**.\n\n"
    "You can ask me about:\n"
    "- **Validation Rules**: Ask about any module (e.g. *'repayment rules'*, *'what validation you used'*, *'customer mandatory fields'*)\n"
    "- **Rule Explanations**: Ask what any rule ID means (e.g. *'What does RPS-018 mean?'*, *'Explain CUST_TC01'*)\n"
    "- **Fintech & LMS Concepts**: DPD, NPA, NACH mandates, Foreclosure, SPDC, LTV, Co-lending, Subvention\n"
    "- **Audit Findings**: Summarize current findings, check why errors occurred, or investigate a specific Loan ID (e.g. *'Show issues for loan 12345'*)\n"
    "- **Remediation**: How to fix specific data violations in your Excel template."
)


class AuditContext:
    """Encapsulates current audit results with record identifiers into compact queryable structures."""

    def __init__(
        self,
        summary: Optional[ValidationSummary] = None,
        results: Optional[List[ValidationResult]] = None,
        source_df: Optional[pd.DataFrame] = None,
        module_name: Optional[str] = None,
        sheet_summaries: Optional[Dict[str, ValidationSummary]] = None,
        sheet_results: Optional[Dict[str, List[ValidationResult]]] = None,
        loan_impact: Optional[Any] = None,
    ):
        self.summary = summary
        self.results = results or []
        self.source_df = source_df
        self.module_name = module_name or (summary.module if summary else "Unknown")
        self.sheet_summaries = sheet_summaries or {}
        self.sheet_results = sheet_results or {}
        self.loan_impact = loan_impact
        self.findings: List[Dict[str, Any]] = self._build_findings()
        self._loan_lookup_index: Dict[str, List[Dict[str, Any]]] = {}
        self._rule_finding_index: Dict[str, List[Dict[str, Any]]] = {}
        self._rebuild_lookup_indexes()

    def _rebuild_lookup_indexes(self) -> None:
        self._loan_lookup_index = self._build_loan_lookup_index()
        self._rule_finding_index = self._build_rule_finding_index()

    def _build_loan_lookup_index(self) -> Dict[str, List[Dict[str, Any]]]:
        index: Dict[str, List[Dict[str, Any]]] = {}
        for finding in self.findings:
            candidates = []
            for key in ["Loan/Customer ID", "Loan ID", "Loan Application Number"]:
                value = str(finding.get(key, "")).strip()
                if value and value not in {"N/A", "Unresolved"}:
                    candidates.append(value)
            if not candidates:
                continue
            for candidate in candidates:
                index.setdefault(candidate.lower(), []).append(finding)
        return index

    def _build_rule_finding_index(self) -> Dict[str, List[Dict[str, Any]]]:
        index: Dict[str, List[Dict[str, Any]]] = {}
        for finding in self.findings:
            rule_id = str(finding.get("Rule ID", "")).strip()
            if not rule_id:
                continue
            index.setdefault(rule_id.upper(), []).append(finding)
        return index

    def get_loan_lookup_index(self) -> Dict[str, List[Dict[str, Any]]]:
        if not self._loan_lookup_index:
            self._loan_lookup_index = self._build_loan_lookup_index()
        return self._loan_lookup_index

    def get_rule_finding_index(self) -> Dict[str, List[Dict[str, Any]]]:
        if not self._rule_finding_index:
            self._rule_finding_index = self._build_rule_finding_index()
        return self._rule_finding_index

    def _build_findings(self) -> List[Dict[str, Any]]:
        findings = []
        id_col = None
        if self.source_df is not None:
            cols_lower = {str(c).strip().lower(): c for c in self.source_df.columns}
            for cand in [
                "loan_id", "loan_application_number", "application_number",
                "customer_id", "applicant_id", "loan_account_no", "account_no"
            ]:
                if cand in cols_lower:
                    id_col = cols_lower[cand]
                    break

        if self.results:
            for r in self.results:
                f = r.to_dict()
                row_num = r.row_number
                entity_id = "N/A"
                if self.source_df is not None and id_col and row_num is not None:
                    try:
                        df_idx = int(row_num) - 2
                        if 0 <= df_idx < len(self.source_df):
                            val = self.source_df.iloc[df_idx][id_col]
                            if pd.notna(val):
                                entity_id = str(val).strip()
                    except (ValueError, TypeError, IndexError):
                        pass

                f["Loan/Customer ID"] = entity_id
                f["Remediation"] = (
                    f"Update '{r.field}' in row {r.row_number} to match '{r.expected_value}'"
                    if r.expected_value else f"Review and correct '{r.field}' at row {r.row_number}"
                )
                findings.append(f)

        for sheet, s_results in self.sheet_results.items():
            for r in s_results:
                f = r.to_dict()
                f["Sheet"] = sheet
                f["Loan/Customer ID"] = "N/A"
                f["Remediation"] = (
                    f"In sheet '{sheet}', update '{r.field}' in row {r.row_number} to match '{r.expected_value}'"
                    if r.expected_value else f"Review and correct '{r.field}' in sheet '{sheet}' at row {r.row_number}"
                )
                findings.append(f)

        return findings

    def has_audit_data(self) -> bool:
        return bool(self.summary or self.sheet_summaries)

    def get_summary_stats(self) -> Dict[str, Any]:
        stats = {}
        if self.sheet_summaries:
            total_records = sum(s.total_records for s in self.sheet_summaries.values())
            total_errors = sum(s.total_errors for s in self.sheet_summaries.values())
            total_warnings = sum(s.total_warnings for s in self.sheet_summaries.values())
            total_passed = sum(s.total_passed for s in self.sheet_summaries.values())
            total_evals = total_passed + total_errors + total_warnings
            score = round((total_passed / total_evals) * 100, 2) if total_evals > 0 else 100.0
            stats = {
                "mode": "workbook",
                "total_sheets": len(self.sheet_summaries),
                "total_records": total_records,
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "total_passed": total_passed,
                "compliance_score": score,
                "sheets": {k: {"errors": v.total_errors, "warnings": v.total_warnings, "records": v.total_records, "module": v.module} for k, v in self.sheet_summaries.items()}
            }
        elif self.summary:
            stats = {
                "mode": "single",
                "module": self.summary.module,
                "total_records": self.summary.total_records,
                "total_rules_checked": self.summary.total_rules_checked,
                "total_passed": self.summary.total_passed,
                "total_errors": self.summary.total_errors,
                "total_warnings": self.summary.total_warnings,
                "compliance_score": self.summary.pass_percentage,
            }
        if stats and self.loan_impact:
            stats["total_unique_affected_loans"] = self.loan_impact.total_unique_affected_loans
            stats["unresolved_findings"] = self.loan_impact.unresolved_findings_count
            stats["resolved_affected_loans"] = self.loan_impact.resolved_affected_loans_count
        return stats


class LLMClient:
    """Isolated LLM client reading API key from environment."""

    def __init__(self):
        self.api_key = (
            os.environ.get("OPENAI_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
        )

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def query(self, prompt: str) -> str:
        if not self.is_configured():
            raise RuntimeError("No LLM API credentials configured in environment.")
        return "LLM integration ready."


class IntentResolver:
    """Deterministic intent classifier for existing knowledge/tool routes."""

    CAPABILITIES_PATTERNS = [
        "what can you do", "what can this assistant help with", "what do you know",
        "tumhe kya kya aata hai", "kya kya aata hai", "aap kya check kar sakte ho",
        "tum kya kya check kar sakte ho", "kya kar sakte ho", "kya jaanta hai",
        "what can this do", "what are you able to do"
    ]
    DATA_CLEANING_PATTERNS = [
        "clean data", "data cleaning", "normalize values", "remove spaces", "trim spaces",
        "lowercase", "uppercase", "standardize", "normalize text", "strip spaces",
        "cleaning", "normalize", "standardize values"
    ]
    CROSS_SHEET_PATTERNS = [
        "compare two sheets", "reconciliation", "reconcile", "mismatch between", "compare sheets",
        "relationship tracing", "link across sheets", "linking key", "cross sheet",
        "across sheets", "sheet mismatch", "compare sheet", "customer for loan", "bank details for loan",
        "show data for loan", "show bank details", "show customer"
    ]
    RECONCILIATION_PATTERNS = [
        "compare charges", "compare receipts", "compare receipts with repayment", "compare charges with disbursal",
        "show reconciliation issues", "receipt mismatches", "charge mismatches", "reconciliation mismatches",
        "how many loans have receipt mismatches", "mismatch", "reconcile"
    ]
    AUDIT_RESULT_PATTERNS = [
        "audit summary", "validation summary", "show issues", "findings", "warnings",
        "failed rules", "current validation errors", "why are there errors", "what are the errors",
        "summary of audit", "overview of errors", "results", "issue summary", "how many errors",
        "how many warnings", "how many findings", "which rules are failing", "rules are failing",
        "failed rule", "which rule is failing", "how many errors are there"
    ]
    LOAN_PATTERNS = [
        "loan issue", "loan problems", "issues for a specific loan", "loan-specific findings",
        "why a loan failed", "why this loan failed", "problem in loan", "loan mein kya problem",
        "loan kyu fail hua", "show issues for loan", "specific loan"
    ]
    GENERAL_DOMAIN_PATTERNS = [
        "dpd", "npa", "nach", "foreclosure", "spdc", "ltv", "co-lending", "subvention",
        "ifsc", "pan", "aadhaar", "cibil", "emi", "principal", "interest rate"
    ]

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.lower().replace("_", " ").replace("-", " ")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @classmethod
    def _contains_any(cls, text: str, patterns: List[str]) -> bool:
        return any(pattern in text for pattern in patterns)

    @classmethod
    def _module_from_question(cls, question: str) -> Optional[str]:
        q = cls._normalize(question)
        aliases = {
            "repayment schedule": "Repayment Schedule",
            "repayment": "Repayment Schedule",
            "customer": "Customer",
            "customers": "Customer",
            "bank details": "Bank Details",
            "bank detail": "Bank Details",
            "loan application": "Loan Application",
            "loans": "Loan Application",
            "charges": "Charges",
            "receipts": "Receipts",
            "payments": "Payments",
            "collateral": "Collateral",
            "disbursal schedule": "Disbursal Schedule",
            "disbursal breakup": "Disbursal Breakup",
        }
        for alias, module_name in aliases.items():
            if alias in q:
                return module_name
        return None

    @classmethod
    def resolve(cls, question: str) -> Dict[str, Any]:
        q = cls._normalize(question)
        if not q:
            return {"intent": "UNKNOWN", "confidence": "low", "entities": {}, "query": question}

        if cls._contains_any(q, cls.CAPABILITIES_PATTERNS):
            return {"intent": "CAPABILITIES", "confidence": "high", "entities": {}, "query": question}

        if re.search(r"\bwhy did .* fail validation\b|\bwhy did .* fail.*\b|\bloan \d+ fail validation\b|\bloan \d+ failed\b", q):
            return {"intent": "TEMPLATE", "confidence": "high", "entities": {"column": q}, "query": question}

        if any(signal in q for signal in cls.AUDIT_RESULT_PATTERNS) or ("why" in q and ("error" in q or "issue" in q or "fail" in q) and "validation" not in q) or "summarize" in q or "summary" in q or ("how many" in q and any(term in q for term in ["error", "errors", "warning", "warnings", "finding", "findings"])) or ("which" in q and "rules" in q and any(term in q for term in ["fail", "failed", "failing"])):
            return {"intent": "AUDIT_RESULT", "confidence": "medium", "entities": {}, "query": question}

        if any(signal in q for signal in ["rule", "validation", "validations", "severity", "check karta", "kaunse validations", "kaunse rules", "rule checks", "what does rule", "what does rps", "what validations are applied", "which rules are available", "validation kya"]) or re.search(r"\b(?:rps|la|cust)[-_]?\d+\b", question, flags=re.IGNORECASE):
            return {"intent": "VALIDATION_RULE", "confidence": "high", "entities": {"module": cls._module_from_question(question)}, "query": question}

        if any(signal in q for signal in cls.LOAN_PATTERNS) or ("loan" in q and any(word in q for word in ["issue", "problem", "fail", "failed", "findings"])):
            return {"intent": "LOAN_INVESTIGATION", "confidence": "high", "entities": {"loan_identifier": re.search(r"\b\d+\b", question)}, "query": question}

        if "cust_idx" in q or "repayment_schedule.status" in q or "." in q and any(token in q for token in ["status", "cust_idx", "loan_application_number", "bank_idx", "gender", "customer_type"]) or any(signal in q for signal in ["allowed values", "control sheet", "readme", "data dictionary", "sheet contains", "which sheet", "column meaning", "meaning of", "relationship", "link across sheets", "core and add-on", "where is ", "kya hai", "kya hota hai", "kya matlab", "matlab", "meaning", "what is ", "what does "]):
            return {"intent": "TEMPLATE", "confidence": "high", "entities": {"column": q}, "query": question}

        if cls._contains_any(q, cls.CROSS_SHEET_PATTERNS):
            return {"intent": "CROSS_SHEET", "confidence": "medium", "entities": {}, "query": question}

        if cls._contains_any(q, cls.RECONCILIATION_PATTERNS):
            return {"intent": "RECONCILIATION", "confidence": "medium", "entities": {}, "query": question}

        if cls._contains_any(q, cls.DATA_CLEANING_PATTERNS):
            return {"intent": "DATA_CLEANING", "confidence": "medium", "entities": {}, "query": question}

        if cls._contains_any(q, cls.GENERAL_DOMAIN_PATTERNS):
            return {"intent": "GENERAL_DOMAIN", "confidence": "medium", "entities": {}, "query": question}

        return {"intent": "UNKNOWN", "confidence": "low", "entities": {}, "query": question}


class AuditAssistant:
    """General-purpose SynoFin Migration Audit Assistant."""

    def __init__(self, context: Optional[AuditContext] = None):
        self.context = context or AuditContext()
        self.llm_client = LLMClient()
        self.template_knowledge = TemplateKnowledgeService()
        self.gemini_agent = GeminiAgent(assistant=self, context=self.context)
        self.last_entity_id: Optional[str] = None
        self.last_rule_id: Optional[str] = None
        self.last_findings_context: List[Dict[str, Any]] = []
        self.conversation_history: List[str] = []
        self._response_cache: Dict[tuple, str] = {}
        self._loan_match_cache: Dict[str, List[Dict[str, Any]]] = {}

    def set_context(self, context: AuditContext) -> None:
        self.context = context
        self._response_cache.clear()
        if hasattr(self.context, "_rebuild_lookup_indexes"):
            self.context._rebuild_lookup_indexes()

    def _resolve_rule_module(self, question: str) -> Optional[str]:
        q = question.lower().replace("_", " ")
        aliases = {
            "repayment schedule": "Repayment Schedule",
            "repayment_schedule": "Repayment Schedule",
            "repayment": "Repayment Schedule",
            "customer": "Customer",
            "customers": "Customer",
            "bank details": "Bank Details",
            "bank_details": "Bank Details",
            "loan application": "Loan Application",
            "loan_application": "Loan Application",
            "charges": "Charges",
            "receipts": "Receipts",
        }
        for alias, module_name in aliases.items():
            if alias in q:
                return module_name
        for mod in RuleKnowledgeBase.list_all_modules():
            mod_norm = mod.lower().replace("_", " ")
            if mod_norm in q or q in mod_norm:
                return mod
        return None

    def _capability_response(self) -> str:
        return (
            "I am your **SynoFin LMS Migration Audit & Fintech Assistant**.\n\n"
            "Here is what I can do:\n"
            "1. **Explore Validation Rules**: Ask about any module (e.g., *'repayment rules'*, *'what validation you used'*, *'customer mandatory fields'*).\n"
            "2. **Rule Explanations**: Ask what any rule ID means (e.g., *'What does RPS-018 mean?'*, *'Explain CUST_TC01'*).\n"
            "3. **Fintech & LMS Concepts**: Ask about DPD, NPA, NACH mandates, Foreclosure, SPDC, LTV, Co-lending, Subvention.\n"
            "4. **Audit Summary**: Summarize current findings and metrics.\n"
            "5. **Analyze Specific Loans**: Check all issues for a specific loan or customer ID (e.g., *'Show all issues for loan 12345'*).\n"
            "6. **Template & Sheet Guidance**: Ask about columns, allowed values, relationships, and workbook structure.\n"
            "7. **Data Cleaning**: Guidance for normalization, trimming, and standardization where supported."
        )

    def _format_rule_result(self, rule_info: Dict[str, Any]) -> str:
        return (
            f"**Rule:** {rule_info['rule_id']}\n"
            f"**Module:** {rule_info['module']}\n"
            f"**Field:** {rule_info['field']}\n"
            f"**Severity:** {rule_info['severity']}\n"
            f"**What it checks:** {rule_info['description']}"
        )

    def _build_rule_finding_index(self) -> Dict[str, List[Dict[str, Any]]]:
        return self.context.get_rule_finding_index() if hasattr(self.context, "get_rule_finding_index") else {}

    def _extract_rule_id(self, question: str) -> Optional[str]:
        matches = re.findall(r"\b[A-Z]{2,}[-_][A-Z0-9-]+\b", question.upper())
        for candidate in matches:
            normalized = candidate.replace("_", "-")
            if RuleKnowledgeBase.find_rule(normalized) is not None:
                return normalized
        return None

    def _handle_rule_findings_query(self, rule_id: str) -> str:
        if not self.context.has_audit_data():
            return "No audit results are currently available. Please upload a source Excel template or master workbook to generate an audit summary."

        if RuleKnowledgeBase.find_rule(rule_id) is None:
            return FALLBACK_MESSAGE

        matches = self._build_rule_finding_index().get(rule_id.upper(), [])
        if not matches:
            return f"**{rule_id}** has no findings in the current audit."

        summary_lines = [
            f"**Current findings for {rule_id}**",
            f"- **Total matching findings:** {len(matches)}",
        ]
        for idx, item in enumerate(matches[:8], 1):
            row_num = item.get("Row Number", "N/A")
            module = item.get("Module", "Unknown")
            field = item.get("Field/Column", "Unknown")
            loan_id = item.get("Loan/Customer ID", "N/A")
            actual = item.get("Actual Value", "")
            expected = item.get("Expected Value", "")
            desc = item.get("Description", "")
            rem = item.get("Remediation", "")
            summary_lines.append(
                f"{idx}. **Row:** {row_num} | **Module:** {module} | **Field:** `{field}` | **Loan/Customer ID:** `{loan_id}`\n"
                f"   - **Actual:** `{actual}`\n"
                f"   - **Expected:** `{expected}`\n"
                f"   - **Description:** {desc}\n"
                f"   - **Fix:** {rem}"
            )
        if len(matches) > 8:
            summary_lines.append(f"... and {len(matches) - 8} additional findings for {rule_id}.")
        return "\n".join(summary_lines)

    def _handle_rule_affected_loans_query(self, rule_id: str) -> str:
        if not self.context.has_audit_data():
            return "No audit results are currently available. Please upload a source Excel template or master workbook to generate an audit summary."

        if RuleKnowledgeBase.find_rule(rule_id) is None:
            return FALLBACK_MESSAGE

        matches = self._build_rule_finding_index().get(rule_id.upper(), [])
        if not matches:
            return f"**{rule_id}** has no affected loans in the current audit."

        if self.context.loan_impact and rule_id in self.context.loan_impact.loan_details_by_rule:
            rule_details = self.context.loan_impact.loan_details_by_rule[rule_id]
            unique = []
            seen = set()
            for item in rule_details:
                loan_val = str(item.get("Loan ID", "")).strip()
                app_val = str(item.get("Loan Application Number", "")).strip()
                key = loan_val or app_val or "Unresolved"
                if key in seen or key == "Unresolved":
                    continue
                seen.add(key)
                unique.append((loan_val, app_val, item.get("Finding Count", 0)))
            if not unique:
                return f"**{rule_id}** has no affected loans in the current audit."
            lines = [f"**Unique affected loans for {rule_id}:** {len(unique)}"]
            for loan_id, app_no, count in unique[:10]:
                lines.append(f"- **{loan_id or app_no or 'Unresolved'}** (Loan App: {app_no or 'N/A'}, findings: {count})")
            if len(unique) > 10:
                lines.append(f"... and {len(unique) - 10} more unique affected loans.")
            return "\n".join(lines)

        unique_loans = {}
        for item in matches:
            loan_key = str(item.get("Loan/Customer ID", "")).strip()
            if loan_key in {"", "N/A"}:
                continue
            unique_loans[loan_key] = unique_loans.get(loan_key, 0) + 1
        if not unique_loans:
            return f"**{rule_id}** has no affected loans in the current audit."
        lines = [f"**Unique affected loans for {rule_id}:** {len(unique_loans)}"]
        for loan_id, count in list(unique_loans.items())[:10]:
            lines.append(f"- **{loan_id}**: {count} finding(s)")
        if len(unique_loans) > 10:
            lines.append(f"... and {len(unique_loans) - 10} more unique affected loans.")
        return "\n".join(lines)

    def _handle_affected_loan_count_query(self) -> str:
        if not self.context.has_audit_data():
            return "No audit results are currently available. Please upload a source Excel template or master workbook to generate an audit summary."

        if self.context.loan_impact is not None:
            count = self.context.loan_impact.total_unique_affected_loans
            return f"**Total affected loans:** {count}"

        if self.context.results:
            impact_findings, loan_impact = LoanIdentificationEngine.analyze_impact(
                self.context.results,
                source_df=self.context.source_df,
                default_module=self.context.module_name,
            )
            self.context.loan_impact = loan_impact
            return f"**Total affected loans:** {loan_impact.total_unique_affected_loans}"

        return "**Total affected loans:** 0"

    def _handle_rule_affected_loan_count_query(self, rule_id: str) -> str:
        if not self.context.has_audit_data():
            return "No audit results are currently available. Please upload a source Excel template or master workbook to generate an audit summary."

        if RuleKnowledgeBase.find_rule(rule_id) is None:
            return FALLBACK_MESSAGE

        if self.context.loan_impact and rule_id in self.context.loan_impact.loan_details_by_rule:
            unique = []
            seen = set()
            for item in self.context.loan_impact.loan_details_by_rule[rule_id]:
                loan_val = str(item.get("Loan ID", "")).strip()
                app_val = str(item.get("Loan Application Number", "")).strip()
                key = loan_val or app_val or "Unresolved"
                if key in seen or key == "Unresolved":
                    continue
                seen.add(key)
                unique.append(loan_val or app_val or "Unresolved")
            return f"**{rule_id}** affects **{len(unique)}** unique loan(s) in the current audit."

        matches = self._build_rule_finding_index().get(rule_id.upper(), [])
        if not matches:
            return f"**{rule_id}** affects **0** unique loan(s) in the current audit."

        unique = {}
        for item in matches:
            loan_key = str(item.get("Loan/Customer ID", "")).strip()
            if loan_key and loan_key not in {"N/A", ""}:
                unique[loan_key] = unique.get(loan_key, 0) + 1
        return f"**{rule_id}** affects **{len(unique)}** unique loan(s) in the current audit."

    def _build_loan_finding_index(self) -> Dict[str, List[Dict[str, Any]]]:
        return self.context.get_loan_lookup_index() if hasattr(self.context, "get_loan_lookup_index") else {}

    def _extract_loan_identifier(self, question: str) -> Optional[str]:
        q = question.strip()
        if not q:
            return None
        q_norm = q.lower()
        loan_keywords = ["loan", "customer", "application number", "app number", "loan id"]

        # Prefer a direct loan-style token like LN-99901 or APP-1001.
        direct_matches = re.findall(r"\b[A-Za-z]{2,}[-_][A-Za-z0-9-]+\b", q)
        for token in direct_matches:
            upper = token.upper()
            if upper.startswith(("RPS-", "LA-", "CUST-", "CUST_", "RPS_", "LA_")):
                continue
            if token.lower() in {"records", "details", "data", "information", "summary", "rows", "sheets"}:
                continue
            if any(keyword in q_norm for keyword in loan_keywords) or "fail" in q_norm or "issue" in q_norm or "problem" in q_norm or "validation" in q_norm:
                return token
            if any(keyword in q_norm for keyword in ["show", "who", "compare", "details", "records", "findings", "issues", "for", "bank", "customer", "receipt", "repayment"]) and "app-" in token.lower():
                return token

        if not any(keyword in q_norm for keyword in loan_keywords) and "fail" not in q_norm and "issue" not in q_norm and "problem" not in q_norm and "validation" not in q_norm:
            if not direct_matches:
                return None
            for token in direct_matches:
                if any(keyword in q_norm for keyword in ["show", "who", "compare", "details", "records", "findings", "issues", "for", "bank", "customer", "receipt", "repayment"]):
                    if token.lower() not in {"records", "details", "data", "information", "summary", "rows", "sheets"}:
                        return token
            return None

        # Accept explicit loan + id phrases as a fallback, including forms like
        # 'show issues for loan MISSING-999' and 'customer APP-1234'.
        loan_id_match = re.search(r"\b(?:loan|customer|application|app)\s*(?:id|number|no)?\s*[:#-]?\s*([A-Za-z0-9][A-Za-z0-9._-]*)", q, flags=re.IGNORECASE)
        if loan_id_match:
            candidate = loan_id_match.group(1).strip()
            if candidate and candidate.lower() not in {"id", "number", "no", "records", "details", "data", "information", "summary", "rows", "sheets"}:
                return candidate

        # Last-resort token extraction for single-value request phrases.
        if any(keyword in q_norm for keyword in loan_keywords):
            for token in re.findall(r"\b[A-Za-z0-9][A-Za-z0-9._-]*\b", q):
                if token.lower() not in {"loan", "customer", "app", "application", "number", "id", "show", "issues", "issue", "details", "records", "data"} and ("-" in token or "_" in token or any(ch.isdigit() for ch in token)):
                    return token

        return None

    def _find_loan_matches(self, loan_identifier: str) -> List[Dict[str, Any]]:
        if not self.context.has_audit_data():
            return []

        normalized = str(loan_identifier).strip()
        if not normalized:
            return []

        cache_key = normalized.lower()
        if cache_key in self._loan_match_cache:
            return self._loan_match_cache[cache_key]

        index = self._build_loan_finding_index()
        exact = index.get(cache_key)
        if exact:
            self._loan_match_cache[cache_key] = exact
            return exact

        matches = []
        for finding in self.context.findings:
            for key in ["Loan/Customer ID", "Loan ID", "Loan Application Number"]:
                value = str(finding.get(key, "")).strip()
                if not value or value == "N/A" or value == "Unresolved":
                    continue
                if value.lower() == cache_key:
                    matches.append(finding)
                    break
        self._loan_match_cache[cache_key] = matches
        return matches

    def _handle_loan_summary_query(self, loan_identifier: str, question: str) -> str:
        matches = self._find_loan_matches(loan_identifier)
        if not matches:
            return f"No audit findings were found for loan {loan_identifier} in the current audit."

        total_findings = len(matches)
        total_errors = sum(1 for f in matches if str(f.get("Severity", "")).upper() == "ERROR")
        total_warnings = sum(1 for f in matches if str(f.get("Severity", "")).upper() == "WARNING")

        q = question.lower()
        if "error" in q and "warning" not in q:
            return f"**Loan {loan_identifier}** has **{total_errors} error(s)** in the current audit."
        if "warning" in q:
            return f"**Loan {loan_identifier}** has **{total_warnings} warning(s)** in the current audit."
        if "issue" in q or "finding" in q or "problem" in q:
            return f"**Loan {loan_identifier}** has **{total_findings} issue(s)** in the current audit."
        return (
            f"**Loan {loan_identifier}**\n"
            f"- **Total Findings:** {total_findings}\n"
            f"- **Errors:** {total_errors}\n"
            f"- **Warnings:** {total_warnings}"
        )

    def _handle_loan_sheet_view(self, loan_identifier: str) -> str:
        matches = self._find_loan_matches(loan_identifier)
        if not matches:
            return f"No audit findings were found for loan {loan_identifier} in the current audit."

        sheet_counts: Dict[str, int] = {}
        for item in matches:
            sheet = str(item.get("Sheet") or item.get("Module") or "Unknown").strip()
            if not sheet:
                sheet = "Unknown"
            sheet_counts[sheet] = sheet_counts.get(sheet, 0) + 1

        lines = [f"**Affected sheets for loan {loan_identifier}:**"]
        for sheet, count in sorted(sheet_counts.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- **{sheet}** — {count} finding(s)")
        return "\n".join(lines)

    def _handle_loan_rule_view(self, loan_identifier: str) -> str:
        matches = self._find_loan_matches(loan_identifier)
        if not matches:
            return f"No audit findings were found for loan {loan_identifier} in the current audit."

        rule_counts: Dict[str, int] = {}
        for item in matches:
            rule_id = str(item.get("Rule ID", "")).strip()
            if not rule_id:
                continue
            rule_counts[rule_id] = rule_counts.get(rule_id, 0) + 1

        lines = [f"**Rules failed for loan {loan_identifier}:**"]
        for rule_id, count in sorted(rule_counts.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- **{rule_id}** — {count} finding(s)")
        return "\n".join(lines)

    def _handle_complete_loan_investigation(self, loan_identifier: str) -> str:
        matches = self._find_loan_matches(loan_identifier)
        if not matches:
            return f"No audit findings were found for loan {loan_identifier} in the current audit."

        total_findings = len(matches)
        total_errors = sum(1 for f in matches if str(f.get("Severity", "")).upper() == "ERROR")
        total_warnings = sum(1 for f in matches if str(f.get("Severity", "")).upper() == "WARNING")

        sheet_counts: Dict[str, int] = {}
        rule_counts: Dict[str, int] = {}
        for item in matches:
            sheet = str(item.get("Sheet") or item.get("Module") or "Unknown").strip()
            sheet_counts[sheet] = sheet_counts.get(sheet, 0) + 1
            rule_id = str(item.get("Rule ID", "")).strip()
            if rule_id:
                rule_counts[rule_id] = rule_counts.get(rule_id, 0) + 1

        lines = [
            f"**Loan:** {loan_identifier}",
            f"**Total Findings:** {total_findings}",
            f"**Errors:** {total_errors}",
            f"**Warnings:** {total_warnings}",
            "",
            "**Affected Sheets:**",
        ]
        for sheet, count in sorted(sheet_counts.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- **{sheet}** — {count} finding(s)")

        lines.extend(["", "**Failed Rules:**"])
        for rule_id, count in sorted(rule_counts.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- **{rule_id}** — {count} finding(s)")

        lines.extend(["", "**Findings (sample):**"])
        for idx, item in enumerate(matches[:10], 1):
            rule_id = item.get("Rule ID", "Unknown")
            module = item.get("Module", item.get("Sheet", "Unknown"))
            field = item.get("Field/Column", "Unknown")
            actual = item.get("Actual Value", "")
            expected = item.get("Expected Value", "")
            description = item.get("Description", "")
            lines.append(
                f"{idx}. **{module}** | **{rule_id}** | **{field}** | **Actual:** `{actual}` | **Expected:** `{expected}` | **{description}**"
            )
        if len(matches) > 10:
            lines.append(f"... and {len(matches) - 10} additional findings for {loan_identifier}.")
        return "\n".join(lines)

    def _handle_loan_investigation_query(self, loan_identifier: str, question: str) -> str:
        q = question.lower()
        if not self.context.has_audit_data():
            return "No audit results are currently available. Please upload a source Excel template or master workbook to generate an audit summary."

        matches = self._find_loan_matches(loan_identifier)
        if not matches:
            return f"No audit findings were found for loan {loan_identifier} in the current audit."

        if "sheet" in q and "issue" in q or "sheet" in q and "problem" in q:
            return self._handle_loan_sheet_view(loan_identifier)
        if "rule" in q and "fail" in q:
            return self._handle_loan_rule_view(loan_identifier)
        if "error" in q and "warning" not in q:
            return self._handle_loan_summary_query(loan_identifier, question)
        if "warning" in q:
            return self._handle_loan_summary_query(loan_identifier, question)
        if "issue" in q or "problem" in q or "validation" in q or "why" in q or "fail" in q:
            return self._handle_complete_loan_investigation(loan_identifier)
        return self._handle_complete_loan_investigation(loan_identifier)

    def _handle_validation_registry_query(self, question: str) -> Optional[str]:
        q = question.strip()
        if not q:
            return None
        q_lower = q.lower()

        if q_lower.startswith("what rules are applied to"):
            return None

        rule_id_matches = re.findall(r"\b[A-Z]{2,}[-_][A-Z0-9-]+\b", q.upper())
        if rule_id_matches:
            for rule_id in rule_id_matches:
                info = RuleKnowledgeBase.find_rule(rule_id)
                if info:
                    if "severity" in q_lower:
                        return f"**Severity:** {info['severity']}"
                    return self._format_rule_result(info)

        if any(kw in q_lower for kw in ["what does rule", "what does ", "what is the severity", "severity of"]) and rule_id_matches:
            return FALLBACK_MESSAGE

        if "severity" in q_lower and any(token in q_lower for token in ["rule", "validation", "validations", "check"]):
            for token in re.findall(r"[A-Za-z0-9_-]+", q):
                cand = token.upper().replace("_", "-")
                info = RuleKnowledgeBase.find_rule(cand)
                if info:
                    return f"**Severity:** {info['severity']}"

        module_name = self._resolve_rule_module(q)
        explicit_module_rule_phrases = [
            "what validations are applied to",
            "which rules are available for",
            "kaunse validations hain",
            "mein kaunse validations hain",
            "kaunse rules hain",
            "validations hain",
        ]
        if module_name and any(term in q_lower for term in explicit_module_rule_phrases):
            rules = RuleKnowledgeBase.get_module_rules(module_name)
            if rules:
                lines = [f"**Validation rules for {module_name}:**"]
                for r in rules[:12]:
                    lines.append(f"- {r.rule_id} | {r.field} | {r.severity.value if hasattr(r.severity, 'value') else str(r.severity)} | {r.description}")
                if len(rules) > 12:
                    lines.append(f"... and {len(rules) - 12} more rules in this module.")
                return "\n".join(lines)

        if any(term in q_lower for term in ["which rule checks", "rule checks", "which rule", "validation for", "check karta", "ka validation", "validation kya", "rule kya"]):
            candidate_keywords = []
            for token in re.findall(r"[A-Za-z0-9_]+", q):
                t = token.lower()
                if t not in {"which", "rule", "checks", "check", "what", "is", "the", "for", "kya", "ka", "hai", "mein", "ye", "this", "validation", "validations", "applied", "available", "in"}:
                    candidate_keywords.append(t)
            if candidate_keywords:
                for kw in candidate_keywords:
                    matches = RuleKnowledgeBase.search_rules_by_keyword(kw)
                    if matches:
                        lines = [f"**Rules matching '{kw}':**"]
                        for m in matches[:5]:
                            lines.append(f"- {m['rule_id']} | {m['field']} | {m['severity']} | {m['description']}")
                        return "\n".join(lines)

        return None

    def _normalize_sheet_alias(self, text: str) -> str:
        t = text.strip().lower().replace("_", " ")
        aliases = {
            "bank detail": "bank_details",
            "bank details": "bank_details",
            "customer": "customers",
            "customers": "customers",
            "repayment schedule": "repayment_schedule",
            "repayment_schedule": "repayment_schedule",
            "loan application": "loans",
            "loans": "loans",
            "control sheet": "CONTROL",
            "control": "CONTROL",
            "readme": "README",
            "data dictionary": "DATA DICTIONARY",
            "related people": "related_people",
            "nach detail": "nach_detail",
            "disbursal schedule": "disbursal_schedule",
            "disbursal breakup": "disbursal_breakup",
            "charges": "charges",
            "receipts": "receipts",
        }
        for key, value in aliases.items():
            if key in t:
                return value
        return ""

    def _format_template_column(self, info: Dict[str, Any]) -> str:
        lines = [
            "Column:",
            str(info.get("column") or "Unknown"),
            "",
            "Sheet:",
            str(info.get("sheet") or "Unknown"),
        ]

        if info.get("type"):
            lines.extend(["", "Type:", str(info["type"])])
        if info.get("requirement"):
            lines.extend(["", "Requirement:", str(info["requirement"])])
        if info.get("allowed_values"):
            allowed = self.template_knowledge._parse_allowed_values(str(info["allowed_values"]))
            if allowed:
                lines.extend(["", "Allowed Values:", ", ".join(allowed)])
        if info.get("description"):
            lines.extend(["", "Meaning:", str(info["description"])])
        if info.get("example") and str(info.get("example")).lower() != "nan":
            lines.extend(["", "Example:", str(info["example"])])
        if info.get("label"):
            lines.extend(["", "Label:", str(info["label"])])

        return "\n".join(lines)

    def _handle_template_query(self, question: str) -> Optional[str]:
        q = question.strip()
        if not q:
            return None
        q_lower = q.lower()

        template_signals = [
            "sheet", "column", "field", "allowed values", "allowed value", "readme", "control sheet",
            "data dictionary", "core and add-on", "relationship", "link across sheets", "matlab",
            "meaning", "what is", "what does", "what are", "value should", "purpose of the control sheet",
            "purpose of this template", "cust_idx", "loan_application_number", "bank_idx", "disbursal_number",
            "status", "customer_type", "gender", "repayment_schedule", "bank_details"
        ]
        validation_signals = [
            "rule", "validation", "error", "audit", "summary", "issue", "finding", "why", "fix it",
            "show all issues", "rps-", "la-", "cust_", "failed validation", "fail validation"
        ]

        if "fail validation" in q_lower or "failed validation" in q_lower or "validation-specific analysis" in q_lower:
            return "I can answer template-related questions here. Validation-specific analysis will be connected in the next stage."

        if re.search(r"\bwhy did .* fail validation\b|\bwhy did .* fail.*\b|\bloan \d+ fail\b|\bloan \d+ failed\b", q_lower):
            return "I can answer template-related questions here. Validation-specific analysis will be connected in the next stage."

        if re.search(r"\b(?:rps|la|cust)[-_]?\d", q_lower):
            return None

        if any(term in q_lower for term in ["what does rule", "what is the severity of", "what is the severity", "what validations are applied to", "which rules are available for", "what rules are applied to", "validation rules", "validation rule", "rules are applied to", "rule checks", "which rule checks", "rule kya", "kaunse validations", "kaunse rules", "validation kya"]):
            return None

        if any(signal in q_lower for signal in validation_signals) and not any(signal in q_lower for signal in template_signals):
            return None

        if any(term in q_lower for term in ["purpose of the control sheet", "what is the purpose of the control sheet", "control sheet" ]):
            control = self.template_knowledge.get_control_knowledge()
            if control and control != "No CONTROL sheet metadata is available because the workbook is not present.":
                return control
            return "This information is not defined in the migration template."

        if any(term in q_lower for term in ["readme", "template instructions", "global rules", "template purpose", "what is the purpose of this template"]):
            readme = self.template_knowledge.get_readme_knowledge()
            if readme:
                return readme
            return "This information is not defined in the migration template."

        if "core and add-on" in q_lower or "core vs add-on" in q_lower or "add-on sheets" in q_lower or "add on sheets" in q_lower:
            return (
                "The workbook defines two groups in the DATA DICTIONARY: CORE and ADD-ON. "
                "CORE sheets are the standard required sheets for live loan migration, while ADD-ON sheets are optional "
                "and should only be filled when the client has that data."
            )

        if "repayment status" in q_lower or "installment status" in q_lower:
            info = self.template_knowledge.get_column_info("repayment_schedule", "status")
            if info:
                return self._format_template_column(info)

        if "which sheet contains" in q_lower or "which sheet has" in q_lower or "sheet contains" in q_lower:
            target = self._normalize_sheet_alias(q_lower)
            if target:
                return f"Sheet:\n{target}"
            for sheet in self.template_knowledge.get_all_sheet_names():
                if sheet.lower() in q_lower:
                    return f"Sheet:\n{sheet}"
            return "This information is not defined in the migration template."

        if "relationship" in q_lower or "link" in q_lower or "link across sheets" in q_lower or "loan records across sheets" in q_lower:
            sample = self.template_knowledge.get_relationships("loans")
            details = []
            for rel in sample[:4]:
                details.append(rel)
            if details:
                return "Relationships:\n" + "\n".join(details)
            return "This information is not defined in the migration template."

        for sheet_name in self.template_knowledge.get_all_sheet_names():
            if sheet_name.lower() == q_lower or q_lower.endswith(sheet_name.lower()) or q_lower in sheet_name.lower():
                info = self.template_knowledge.get_sheet_info(sheet_name)
                if info:
                    return "Sheet:\n" + sheet_name + "\n\nColumns:\n" + ", ".join(info.get("columns", [])[:10])

        if "." in q_lower:
            target = q_lower.split("?")[0].strip()
            sheet_part, _, field_part = target.partition(".")
            sheet_name = self._normalize_sheet_alias(sheet_part)
            if not sheet_name:
                seen = False
                for sheet in self.template_knowledge.get_all_sheet_names():
                    if sheet.lower() == sheet_part:
                        sheet_name = sheet
                        seen = True
                        break
                if not seen:
                    sheet_name = sheet_part
            info = self.template_knowledge.get_column_info(sheet_name, field_part)
            if info:
                return self._format_template_column(info)

        raw_tokens = re.findall(r"[A-Za-z0-9_]+", q)
        if raw_tokens:
            for token in raw_tokens:
                if token.lower() in {"what", "is", "does", "mean", "ka", "kya", "matlab", "hai", "the", "for", "of", "this", "in", "and", "or", "are", "allowed", "values", "which", "sheet", "contains", "purpose", "how", "do", "i", "link", "loan", "records", "across", "questions", "question"}:
                    continue
                if token.lower() == "cust_idx":
                    info = self.template_knowledge.get_column_info("customers", "cust_idx")
                    if info:
                        return self._format_template_column(info)
                if token.lower() == "status":
                    info = self.template_knowledge.get_column_info("repayment_schedule", "status")
                    if info:
                        return self._format_template_column(info)
                info = self.template_knowledge.get_column_info("", token)
                if info:
                    return self._format_template_column(info)

                for entry in self.template_knowledge.get_data_dictionary():
                    if token.lower() in str(entry.get("column", "")).lower() or token.lower() in str(entry.get("sheet", "")).lower():
                        return self._format_template_column(entry)

        for field_name in ["cust_idx", "status", "loan_application_number", "bank_idx", "disbursal_number", "gender", "customer_type", "payment_status"]:
            if field_name.lower() in q_lower:
                for sheet_name in self.template_knowledge.get_all_sheet_names():
                    info = self.template_knowledge.get_column_info(sheet_name, field_name)
                    if info:
                        return self._format_template_column(info)

        if any(term in q_lower for term in ["allowed values", "allowed value", "type of value", "what type", "meaning", "mean", "matlab", "value should", "what is the column", "what does"]):
            for entry in self.template_knowledge.get_data_dictionary():
                col = str(entry.get("column") or "").lower()
                sheet = str(entry.get("sheet") or "").lower()
                tokens = re.findall(r"[a-z0-9_]+", q_lower)
                if any(token in col for token in tokens) or any(token in sheet for token in tokens):
                    return self._format_template_column(entry)

        if any(term in q_lower for term in ["what is ", "what does ", "what are ", "status ka", "ka kya matlab", "kya matlab", "what is the purpose", "what is this"]):
            for entry in self.template_knowledge.get_data_dictionary():
                col = str(entry.get("column") or "").lower()
                if col in q_lower:
                    return self._format_template_column(entry)

        return "This information is not defined in the migration template."

    def _get_sheet_dfs(self) -> Dict[str, pd.DataFrame]:
        sheet_dfs = getattr(self.context, "sheet_dfs", None)
        if isinstance(sheet_dfs, dict):
            return {str(k): v for k, v in sheet_dfs.items() if isinstance(v, pd.DataFrame)}

        workbook_dfs = getattr(self.context, "workbook_dfs", None)
        if isinstance(workbook_dfs, dict):
            return {str(k): v for k, v in workbook_dfs.items() if isinstance(v, pd.DataFrame)}

        if self.context.source_df is not None:
            key = self.context.module_name or "source"
            return {str(key): self.context.source_df}
        return {}

    def _normalize_loan_key(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().lower().replace(" ", "")

    def _find_rows_for_loan(self, loan_identifier: str) -> Dict[str, List[Dict[str, Any]]]:
        frames = self._get_sheet_dfs()
        if not frames:
            return {}

        loan_key = self._normalize_loan_key(loan_identifier)
        if not loan_key:
            return {}

        matched: Dict[str, List[Dict[str, Any]]] = {}
        for sheet_name, df in frames.items():
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue
            cols = {str(col).strip().lower().replace(" ", "_"): col for col in df.columns}
            candidate_cols = []
            for name in ["loan_application_number", "application_number", "loan_id", "loanid", "account_no", "customer_id", "cust_idx", "bank_idx", "disbursal_number", "receipt_id", "charge_id", "repayment_schedule_id"]:
                if name in cols:
                    candidate_cols.append(cols[name])
            if not candidate_cols:
                continue

            for row in df.to_dict(orient="records"):
                for col in candidate_cols:
                    value = row.get(col)
                    if value is None or pd.isna(value):
                        continue
                    if self._normalize_loan_key(value) == loan_key:
                        matched.setdefault(str(sheet_name), []).append(row)
                        break
        return matched

    def _find_rows_in_sheet(self, sheet_name: str, loan_identifier: Optional[str] = None) -> List[Dict[str, Any]]:
        frames = self._get_sheet_dfs()
        if sheet_name not in frames:
            return []
        df = frames[sheet_name]
        if df.empty:
            return []

        rows = df.to_dict(orient="records")
        if loan_identifier is None:
            return rows
        loan_key = self._normalize_loan_key(loan_identifier)
        if not loan_key:
            return []
        filtered = []
        for row in rows:
            for key, value in row.items():
                key_norm = str(key).strip().lower().replace(" ", "_")
                if key_norm in {"loan_application_number", "application_number", "loan_id", "loanid", "account_no", "customer_id"}:
                    if self._normalize_loan_key(value) == loan_key:
                        filtered.append(row)
                        break
        return filtered

    def _format_cross_sheet_rows(self, sheet_name: str, rows: List[Dict[str, Any]]) -> str:
        if not rows:
            return ""
        display_name = sheet_name.replace("_", " ").title()
        for name, label in {"bank_details": "Bank Details", "nach_detail": "NACH", "repayment_schedule": "Repayment", "charges": "Charges", "receipts": "Receipts", "excess_money": "Excess Money", "disbursal_schedule": "Disbursal", "disbursal_breakup": "Disbursal Breakup", "customers": "Customers"}.items():
            if sheet_name.lower() == name:
                display_name = label
                break
        lines = [f"{display_name}:"]
        for idx, row in enumerate(rows[:3], 1):
            detail_bits = []
            for key, value in row.items():
                if str(value).strip() in {"", "nan", "NaN", "None", "N/A"}:
                    continue
                if str(key).lower() in {"loan_application_number", "loan_id", "customer_id", "cust_idx", "bank_idx", "receipt_id", "charge_id", "disbursal_number", "umrn", "status"}:
                    detail_bits.append(f"{key}: {value}")
                elif any(token in str(key).lower() for token in ["amount", "balance", "principal", "interest", "received", "charge", "excess"]):
                    detail_bits.append(f"{key}: {value}")
            if not detail_bits:
                detail_bits = [f"{key}: {value}" for key, value in list(row.items())[:4]]
            lines.append(f"{idx}. " + "; ".join(detail_bits))
        if len(rows) > 3:
            lines.append(f"... and {len(rows) - 3} more records")
        return "\n".join(lines)

    def _handle_cross_sheet_loan_summary(self, loan_identifier: str) -> str:
        frames = self._get_sheet_dfs()
        if not frames:
            return f"No workbook data is currently loaded for loan {loan_identifier}."

        matched = self._find_rows_for_loan(loan_identifier)
        if not matched:
            return f"No linked records were found for loan {loan_identifier} in the current workbook data."

        lines = [f"Loan: {loan_identifier}"]
        ordered_sheets = ["customers", "bank_details", "nach_detail", "disbursal_schedule", "disbursal_breakup", "repayment_schedule", "charges", "receipts", "excess_money"]
        for sheet_name in ordered_sheets:
            rows = matched.get(sheet_name, [])
            if rows:
                lines.append("")
                lines.append(self._format_cross_sheet_rows(sheet_name, rows))
        return "\n".join(lines)

    def _handle_cross_sheet_lookup(self, question: str, loan_identifier: Optional[str] = None) -> str:
        if not loan_identifier:
            loan_identifier = self._extract_loan_identifier(question)
        if not loan_identifier:
            return "No loan identifier was found in the current workbook data for that cross-sheet lookup."

        q = question.lower()
        target_sheets = {
            "customer": "customers",
            "bank": "bank_details",
            "nach": "nach_detail",
            "repayment": "repayment_schedule",
            "charge": "charges",
            "receipt": "receipts",
            "disbursal": "disbursal_schedule",
        }

        for keyword, sheet_name in target_sheets.items():
            if keyword in q:
                rows = self._find_rows_in_sheet(sheet_name, loan_identifier)
                if not rows:
                    return f"No {sheet_name.replace('_', ' ')} records were found for loan {loan_identifier}."
                row = rows[0]
                if sheet_name == "customers":
                    for key in ["customer_name", "name", "customer", "first_name"]:
                        if key in row:
                            return f"Customer for loan {loan_identifier}: {row[key]}"
                    return f"Customer record for loan {loan_identifier}: {row}"
                if sheet_name == "bank_details":
                    bits = []
                    for key in ["bank_name", "ifsc", "bank_idx", "account_no"]:
                        if key in row:
                            bits.append(f"{key}: {row[key]}")
                    if bits:
                        return f"Bank details for loan {loan_identifier}: " + "; ".join(bits)
                    return f"Bank details for loan {loan_identifier}: {row}"
                if sheet_name == "nach_detail":
                    return f"NACH details for loan {loan_identifier}: {row}"
                if sheet_name == "repayment_schedule":
                    key_fields = ["status", "received_amount", "outstanding_amount", "principal_amount", "interest_amount"]
                    values = "; ".join(f"{k}: {row[k]}" for k in key_fields if k in row)
                    return f"Repayment schedule for loan {loan_identifier}: {values or row}"
                if sheet_name == "charges":
                    amount_field = next((k for k in row if "amount" in k.lower() or "charge" in k.lower()), None)
                    return f"Charge details for loan {loan_identifier}: {amount_field or 'amount'} = {row.get(amount_field, row)}"
                if sheet_name == "receipts":
                    amount_field = next((k for k in row if "amount" in k.lower() or "receipt" in k.lower()), None)
                    return f"Receipt details for loan {loan_identifier}: {amount_field or 'amount'} = {row.get(amount_field, row)}"
                if sheet_name == "disbursal_schedule":
                    return f"Disbursal record for loan {loan_identifier}: {row}"

        if "all sheets" in q or "across all sheets" in q or "across sheets" in q:
            return self._handle_cross_sheet_loan_summary(loan_identifier)

        return self._handle_cross_sheet_loan_summary(loan_identifier)

    def _detect_amount_column(self, df: pd.DataFrame, preferred_names: List[str]) -> Optional[str]:
        cols = {str(col).strip().lower().replace(" ", "_"): col for col in df.columns}
        for pref in preferred_names:
            norm = pref.strip().lower().replace(" ", "_")
            if norm in cols:
                return cols[norm]
        for col in df.columns:
            lower = str(col).strip().lower()
            if any(term in lower for term in ["amount", "balance", "principal", "charge", "receipt", "received", "paid"]):
                return str(col)
        return None

    def _coerce_amount(self, value: Any) -> float:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return 0.0
        try:
            if isinstance(value, str):
                cleaned = value.replace(",", "").replace("₹", "").replace("Rs", "").strip()
                if cleaned.lower() in {"nan", "n/a", "none", ""}:
                    return 0.0
                return float(cleaned)
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _compute_reconciliation_summary(self, source_sheet: str, target_sheet: str, loan_identifier: Optional[str] = None) -> Optional[Dict[str, Any]]:
        frames = self._get_sheet_dfs()
        if not frames:
            return None
        if source_sheet not in frames or target_sheet not in frames:
            return None

        source_df = frames[source_sheet]
        target_df = frames[target_sheet]
        source_col = self._detect_amount_column(source_df, ["amount", "received_amount", "charge_amount", "disbursal_amount", "receipt_amount", "excess_amount", "principal_amount", "interest_amount"])
        target_col = self._detect_amount_column(target_df, ["amount", "received_amount", "charge_amount", "disbursal_amount", "receipt_amount", "excess_amount", "principal_amount", "interest_amount"])
        if source_col is None or target_col is None:
            return None

        source_total = 0.0
        target_total = 0.0
        loan_keys = set()
        if loan_identifier is not None:
            loan_key = self._normalize_loan_key(loan_identifier)
        else:
            loan_key = None

        for df, value_col in [(source_df, source_col), (target_df, target_col)]:
            for row in df.to_dict(orient="records"):
                if loan_key is not None:
                    found = False
                    for key_name, value in row.items():
                        if str(key_name).strip().lower().replace(" ", "_") in {"loan_application_number", "application_number", "loan_id", "loanid", "account_no"}:
                            if self._normalize_loan_key(value) == loan_key:
                                found = True
                                break
                    if not found:
                        continue
                if value_col in row:
                    if loan_key is not None:
                        for key_name, value in row.items():
                            if str(key_name).strip().lower().replace(" ", "_") in {"loan_application_number", "application_number", "loan_id", "loanid", "account_no"}:
                                loan_keys.add(self._normalize_loan_key(value))
                    if df is source_df:
                        source_total += self._coerce_amount(row[value_col])
                    else:
                        target_total += self._coerce_amount(row[value_col])

        if loan_identifier is not None and not loan_keys:
            return None

        difference = source_total - target_total
        return {
            "source_sheet": source_sheet,
            "target_sheet": target_sheet,
            "source_amount": round(source_total, 2),
            "target_amount": round(target_total, 2),
            "difference": round(difference, 2),
            "status": "MATCH" if abs(difference) <= 0.01 else "MISMATCH",
            "loan_identifier": loan_identifier,
            "loan_count": len(loan_keys) if loan_identifier is None else 1,
        }

    def _handle_reconciliation_question(self, question: str) -> str:
        q = question.lower()
        loan_identifier = self._extract_loan_identifier(question)

        if "how many loans have" in q and "mismatch" in q:
            frames = self._get_sheet_dfs()
            source_df = frames.get("receipts")
            target_df = frames.get("repayment_schedule")
            if source_df is None or target_df is None:
                return "Reconciliation rule not defined in current template/business rules."

            loans = set()
            for df, col_name in [(source_df, "receipt_id"), (target_df, "loan_application_number")]:
                for row in df.to_dict(orient="records"):
                    for key_name, value in row.items():
                        if str(key_name).strip().lower().replace(" ", "_") in {"loan_application_number", "application_number", "loan_id", "loanid"}:
                            if value is not None and not pd.isna(value):
                                loans.add(self._normalize_loan_key(value))
            mismatches = 0
            for loan_key in sorted(loans):
                summary = self._compute_reconciliation_summary("receipts", "repayment_schedule", loan_identifier=loan_key if loan_key else None)
                if summary and summary["status"] == "MISMATCH":
                    mismatches += 1
            return f"**Receipt mismatches:** {mismatches} unique loan(s)."

        if "charges" in q and "disbursal" in q:
            summary = self._compute_reconciliation_summary("charges", "disbursal_breakup", loan_identifier=loan_identifier)
            if summary is None:
                return "Reconciliation rule not defined in current template/business rules."
            return (
                f"Reconciliation: Charges vs Disbursal Breakup\n"
                f"Loan: {summary['loan_identifier'] or 'All matched loans'}\n"
                f"Source Amount: {summary['source_amount']}\n"
                f"Target Amount: {summary['target_amount']}\n"
                f"Difference: {summary['difference']}\n"
                f"Status: {summary['status']}"
            )

        if "receipts" in q and "repayment" in q:
            summary = self._compute_reconciliation_summary("receipts", "repayment_schedule", loan_identifier=loan_identifier)
            if summary is None:
                return "Reconciliation rule not defined in current template/business rules."
            return (
                f"Reconciliation: Receipts vs Repayment Schedule\n"
                f"Loan: {summary['loan_identifier'] or 'All matched loans'}\n"
                f"Source Amount: {summary['source_amount']}\n"
                f"Target Amount: {summary['target_amount']}\n"
                f"Difference: {summary['difference']}\n"
                f"Status: {summary['status']}"
            )

        if "receipts" in q and "charges" in q:
            summary = self._compute_reconciliation_summary("receipts", "charges", loan_identifier=loan_identifier)
            if summary is None:
                return "Reconciliation rule not defined in current template/business rules."
            return (
                f"Reconciliation: Receipts vs Charges\n"
                f"Loan: {summary['loan_identifier'] or 'All matched loans'}\n"
                f"Source Amount: {summary['source_amount']}\n"
                f"Target Amount: {summary['target_amount']}\n"
                f"Difference: {summary['difference']}\n"
                f"Status: {summary['status']}"
            )

        if "receipt" in q and "excess" in q:
            summary = self._compute_reconciliation_summary("receipts", "excess_money", loan_identifier=loan_identifier)
            if summary is None:
                return "Reconciliation rule not defined in current template/business rules."
            return (
                f"Reconciliation: Receipts vs Excess Money\n"
                f"Loan: {summary['loan_identifier'] or 'All matched loans'}\n"
                f"Source Amount: {summary['source_amount']}\n"
                f"Target Amount: {summary['target_amount']}\n"
                f"Difference: {summary['difference']}\n"
                f"Status: {summary['status']}"
            )

        if "reconciliation issues" in q or "show reconciliation" in q or "mismatch" in q:
            issues = []
            for (source, target) in [("charges", "disbursal_breakup"), ("receipts", "repayment_schedule"), ("receipts", "charges"), ("receipts", "excess_money")]:
                summary = self._compute_reconciliation_summary(source, target, loan_identifier=loan_identifier)
                if summary is not None:
                    issues.append(f"{source.title()} vs {target.title()}: {summary['status']} (difference={summary['difference']})")
            if not issues:
                return "Reconciliation rule not defined in current template/business rules."
            return "\n".join(issues)

        return "Reconciliation rule not defined in current template/business rules."

    def _response_cache_key(self, question: str) -> tuple:
        summary = getattr(self.context, "summary", None)
        return (
            question.strip().lower(),
            id(self.context),
            len(getattr(self.context, "findings", [])),
            getattr(summary, "module", None),
            len(getattr(self.context, "results", [])),
            len(getattr(self.context, "sheet_results", {})),
        )

    def ask(self, question: str) -> str:
        q = question.strip().lower()
        if not q:
            return "Please type a question about SynoFin migration rules, banking concepts, or audit findings."

        cache_key = self._response_cache_key(question)
        if cache_key in self._response_cache:
            return self._response_cache[cache_key]

        # 1. Natural conversation & Greetings (English & Hindi/Hinglish)
        greetings = ["hi", "hello", "hey", "hii", "hola", "namaste", "pranam"]
        if q in greetings or any(q.startswith(g + " ") for g in greetings):
            return "Hello. I’m the SynoFin Migration Audit Assistant. I can explain validation rules, audit findings, affected records, banking concepts, and remediation guidance. What would you like to check?"

        # Casual Hindi inquiries
        if any(h in q for h in ["kya hal hai", "kya haal hai", "kaise ho", "how are you"]):
            return "Main bilkul badhiya hoon! Main SynoFin LMS migration data validation aur business rules audit me aapki madad karne ke liye tayar hoon. Aap apne template, validation rules ya errors ke baare me koi bhi sawal puch sakte hain!"

        extracted_rule_id = self._extract_rule_id(question)
        if extracted_rule_id:
            q_norm = q.lower()
            if any(term in q_norm for term in ["show findings for", "findings for", "what errors are coming for", "errors for", "failures for", "failures?", "show issues for", "issue for", "findings of"]):
                return self._handle_rule_findings_query(extracted_rule_id)
            if any(term in q_norm for term in ["which loans failed", "show affected loans for", "which loans have this issue", "affected loans for", "loan failed", "loans failed"]):
                return self._handle_rule_affected_loans_query(extracted_rule_id)
            if any(term in q_norm for term in ["how many loans failed", "how many loans are affected by", "how many loans are impacted by", "how many affected loans for"]):
                return self._handle_rule_affected_loan_count_query(extracted_rule_id)

        unknown_rule_candidate = None
        for candidate in re.findall(r"\b[A-Z]{2,}[-_][A-Z0-9-]+\b", question.upper()):
            normalized = candidate.replace("_", "-")
            if RuleKnowledgeBase.find_rule(normalized) is None:
                unknown_rule_candidate = normalized
                break
        if unknown_rule_candidate and "loan" not in q and "customer" not in q and any(term in q for term in ["show findings for", "findings for", "show issues for", "issue for", "which loans failed", "show affected loans for", "how many loans failed", "what does rule", "what does "]):
            return FALLBACK_MESSAGE

        if any(term in q for term in ["what validations are applied to", "which rules are available for", "what rules are applied to", "validation rules", "which validation rules"]):
            validation_registry_resp = self._handle_validation_registry_query(question)
            if validation_registry_resp is not None:
                return validation_registry_resp

        loan_identifier = self._extract_loan_identifier(question)
        if loan_identifier and self.context.has_audit_data():
            q_norm = q.lower()
            if any(term in q_norm for term in ["error", "errors", "warning", "warnings", "issue", "issues", "problem", "problems", "validation", "fail", "failed", "why did", "show all", "show issues", "validation issues", "what problems", "what issues", "rules failed"]):
                matches = self._find_loan_matches(loan_identifier)
                if matches:
                    self.last_entity_id = loan_identifier
                    self.last_findings_context = matches
                    return self._handle_loan_investigation_query(loan_identifier, question)
                return self._handle_loan_investigation_query(loan_identifier, question)

        if any(term in q for term in ["how many loans are affected", "how many unique loans have issues", "total affected loans", "total unique loans affected", "affected loan count"]):
            return self._handle_affected_loan_count_query()

        if "compare" in q or "reconciliation" in q or "mismatch" in q or "show reconciliation issues" in q:
            return self._handle_reconciliation_question(question)

        loan_identifier = self._extract_loan_identifier(question)
        if loan_identifier and loan_identifier.lower() not in {"records", "details", "data", "information", "summary", "rows", "sheets"}:
            if ("show data for loan" in q or "across all sheets" in q or "across sheets" in q or "who is the customer for loan" in q or "show bank details for loan" in q or "show bank details for" in q or "show nach details for" in q or "show repayment records for" in q or "show charges for" in q or "show receipts for" in q or "which customer is linked to loan" in q):
                return self._handle_cross_sheet_lookup(question, loan_identifier)

        # Intent resolver sits before the legacy tool-specific branches.
        intent = IntentResolver.resolve(question)
        intent_name = intent["intent"]

        if intent_name == "CAPABILITIES":
            return self._capability_response()

        if intent_name == "VALIDATION_RULE":
            validation_registry_resp = self._handle_validation_registry_query(question)
            if validation_registry_resp is not None:
                return validation_registry_resp

        if intent_name == "AUDIT_RESULT":
            return self._handle_audit_result_query(question)

        if intent_name == "RECONCILIATION":
            return self._handle_reconciliation_question(question)

        if intent_name == "CROSS_SHEET":
            extracted = self._extract_loan_identifier(question)
            if extracted and extracted.lower() not in {"records", "details", "data", "information", "summary", "rows", "sheets"}:
                return self._handle_cross_sheet_lookup(question, extracted)
            template_resp = self._handle_template_query(question)
            if template_resp is not None:
                return template_resp
            return "This information is not defined in the migration template."

        if self._is_follow_up(q):
            return self._handle_follow_up(q)

        if intent_name == "UNKNOWN":
            if self.gemini_agent.is_configured():
                self.conversation_history.append(question)
                return self.gemini_agent.answer(question, context=self.context, history=self.conversation_history)
            return UNKNOWN_INTENT_MESSAGE

        if intent_name == "DATA_CLEANING":
            return (
                "The project includes data-cleaning utilities for value normalization, trimming spaces, and standardizing common text values. "
                "For a specific cleaning question, ask about a field or value pattern and I can guide you to the supported normalization approach."
            )

        if intent_name == "GENERAL_DOMAIN":
            fintech_resp = lookup_fintech_concept(q)
            if fintech_resp:
                return fintech_resp

        if intent_name == "TEMPLATE":
            template_resp = self._handle_template_query(question)
            if template_resp is not None:
                return template_resp
            return "This information is not defined in the migration template."

        if intent_name == "VALIDATION_RULE":
            validation_registry_resp = self._handle_validation_registry_query(question)
            if validation_registry_resp is not None:
                return validation_registry_resp

        # Capabilities / Help inquiries
        if any(term in q for term in ["what can you do", "help", "who are you", "capabilities", "kya kar sakte ho", "kya kr skte ho"]):
            return self._capability_response()

        validation_registry_resp = self._handle_validation_registry_query(question)
        if validation_registry_resp is not None:
            return validation_registry_resp

        template_resp = self._handle_template_query(question)
        if template_resp is not None:
            return template_resp

        # "What validation you used" / Overall validations query
        if any(term in q for term in ["what validation", "validations used", "which validation", "validation rules used"]):
            return self._handle_all_validations_overview()

        # 2. Smart Follow-Up Handling
        if self._is_follow_up(q):
            return self._handle_follow_up(q)

        # 3. Specific Loan / Customer ID Analysis
        tokens = re.findall(r"\b[A-Za-z0-9\-_]{2,}\b", question)
        for token in tokens:
            if token.lower() in [
                "loan", "customer", "this", "finding", "about", "what", "issue", "show", "tell",
                "explain", "check", "for", "rule", "rules", "module", "how", "fix", "why", "kya"
            ]:
                continue
            matched = [
                f for f in self.context.findings
                if str(f.get("Loan/Customer ID", "")).lower() == token.lower()
                or token.lower() in str(f.get("Actual Value", "")).lower()
            ]
            if matched:
                self.last_entity_id = token
                self.last_findings_context = matched
                return self._handle_loan_analysis(token, matched)

        if ("loan" in q or "customer" in q) and any(w in q for w in ["issue", "finding", "show", "check", "batao", "problem"]):
            words = [w for w in tokens if w.lower() not in ["show", "all", "issues", "for", "loan", "customer", "is", "failing", "why", "check", "the", "with"]]
            if words:
                cand_loan = words[0]
                if self.context.has_audit_data():
                    return f"Loan '{cand_loan}' was not found in the current audit data."
                else:
                    return f"No audit data is currently loaded to search for loan '{cand_loan}'. Please upload and audit an Excel file first."

        # 4. Module Rules Queries (e.g. "repayment", "repayment schedule", "customer rules")
        module_resp = self._handle_module_query(q)
        if module_resp:
            return module_resp

        # 5. Rule ID Explanation Query (e.g. "RPS-018", "CUST_TC01", "LA-001")
        for token in tokens:
            cand = token.upper().replace("_", "-")
            rule_info = RuleKnowledgeBase.find_rule(cand)
            if rule_info:
                self.last_rule_id = rule_info["rule_id"]
                return self._handle_rule_explanation(rule_info)

        # 6. Fintech / LMS / Banking Concept dictionary lookup
        fintech_resp = lookup_fintech_concept(q)
        if fintech_resp:
            return fintech_resp

        # 7. Concept / Keyword search across rules (e.g. "closing balance", "pending_amount")
        concept_resp = self._handle_concept_rule_search(q)
        if concept_resp:
            return concept_resp

        # 8. Audit Summary Query
        if any(term in q for term in ["summarize", "summary", "audit summary", "overview", "status", "score"]):
            if not self.context.has_audit_data():
                return "No audit results are currently available. Please upload a source Excel template or master workbook to generate an audit summary."
            return self._handle_audit_summary()

        # 9. "Why are there errors?" / Major issues
        if ("why" in q and any(w in q for w in ["error", "issue", "fail"])) or any(term in q for term in ["major issue", "major issues", "top error", "top issue", "show major"]):
            if not self.context.has_audit_data():
                return "No audit has been run yet. Please upload an Excel file to evaluate errors."
            return self._handle_why_errors_grouped()

        # 10. "Explain this finding" / "How to fix"
        if any(term in q for term in ["explain finding", "explain this finding", "how to fix", "fix this", "remediation"]):
            if self.context.findings:
                return self._handle_explain_findings(self.context.findings[:5])
            else:
                return "There are no violation findings in the current audit dataset to explain."

        # Fallback with friendly domain guidance
        return FALLBACK_MESSAGE

    def _handle_all_validations_overview(self) -> str:
        all_mods = RuleKnowledgeBase.list_all_modules()
        total_rules = sum(len(RuleKnowledgeBase.get_module_rules(m)) for m in all_mods)
        lines = [
            f"**SynoFin Migration Validation Architecture:**\n",
            f"The audit engine evaluates **{total_rules}+ enterprise business rules** across **{len(all_mods)} specialized domains**:\n",
            "1. **Core Loan Applications:** Loan ID uniqueness, product & scheme codes, interest rate bounds, tenure, financial amounts, moratorium, colending, subvention.",
            "2. **Customer Demographics & KYC:** PAN format (10-char regex), Aadhaar validation, phone uniqueness, CIBIL score ranges (300-900), DOB validity.",
            "3. **Repayment Schedule:** Carry-forward balance continuity (`closing = opening - principal`), status vs received/pending amounts, FC foreclosure checks, part payments.",
            "4. **Collateral & Security:** Market valuation, LTV ratio adherence, property/vehicle/gold parameters, SPDC/PDC verification.",
            "5. **Banking & Payments:** IFSC format (`^[A-Z]{4}0[A-Z0-9]{6}$`), NACH UMRN mandates, disbursal schedule vs breakup consistency.",
            "\n*You can type any module name (e.g. 'repayment', 'customer', 'bank_details') to see its specific rules.*"
        ]
        return "\n".join(lines)

    def _is_follow_up(self, q: str) -> bool:
        follow_up_cues = ["second one", "first one", "third one", "next one", "how do i fix it", "how to fix it", "explain that", "what about that"]
        return any(cue in q for cue in follow_up_cues) and (bool(self.last_findings_context) or bool(self.last_rule_id))

    def _handle_follow_up(self, q: str) -> str:
        if "second one" in q and len(self.last_findings_context) >= 2:
            target = self.last_findings_context[1]
            return (
                f"**Second Finding Details:**\n"
                f"- **Rule ID:** {target.get('Rule ID')}\n"
                f"- **Column / Field:** `{target.get('Field/Column')}`\n"
                f"- **Severity:** {target.get('Severity')}\n"
                f"- **Row Number:** {target.get('Row Number')}\n"
                f"- **Found Value:** `{target.get('Actual Value')}`\n"
                f"- **Expected Condition:** `{target.get('Expected Value')}`\n"
                f"- **Context:** {target.get('Description')}\n"
                f"- **How to Fix:** {target.get('Remediation')}"
            )
        elif "first one" in q and len(self.last_findings_context) >= 1:
            target = self.last_findings_context[0]
            return (
                f"**First Finding Details:**\n"
                f"- **Rule ID:** {target.get('Rule ID')}\n"
                f"- **Column / Field:** `{target.get('Field/Column')}`\n"
                f"- **Row Number:** {target.get('Row Number')}\n"
                f"- **Found Value:** `{target.get('Actual Value')}`\n"
                f"- **Expected Condition:** `{target.get('Expected Value')}`\n"
                f"- **How to Fix:** {target.get('Remediation')}"
            )
        elif "fix" in q:
            if self.last_findings_context:
                target = self.last_findings_context[0]
                return f"**Fix Guidance for {target.get('Rule ID')} (`{target.get('Field/Column')}`):**\n\n{target.get('Remediation')}"
            elif self.last_rule_id:
                r_info = RuleKnowledgeBase.find_rule(self.last_rule_id)
                if r_info:
                    return f"**Fix Guidance for {r_info['rule_id']}:**\n\nIn column `{r_info['field']}`, ensure values satisfy: {r_info['description']}."

        return "Could not determine which finding to follow up on. Please mention the specific Rule ID or Loan ID."

    def _handle_module_query(self, q: str) -> Optional[str]:
        """Detect and answer questions about rules in any module."""
        # Check alias synonyms
        q_norm = q.replace("_", " ").strip()
        synonyms = {
            "repayment": "Repayment Schedule",
            "schedule": "Repayment Schedule",
            "loan": "Loan Application",
            "loans": "Loan Application",
            "customer": "Customer",
            "customers": "Customer",
            "collateral": "Collateral",
            "bank": "Bank Details",
            "bank details": "Bank Details",
            "disbursal": "Disbursal Schedule",
            "charges": "Charges",
            "receipts": "Receipts",
            "nach": "Nach Detail",
        }

        matched_mod = None
        for syn, target in synonyms.items():
            if re.search(r"\b" + re.escape(syn) + r"\b", q_norm):
                matched_mod = target
                break

        if not matched_mod:
            for mod in RuleKnowledgeBase.list_all_modules():
                m_norm = mod.lower()
                if m_norm in q_norm or m_norm.replace(" ", "") in q_norm.replace(" ", ""):
                    matched_mod = mod
                    break

        if matched_mod:
            rules = RuleKnowledgeBase.get_module_rules(matched_mod)
            req_cols = RuleKnowledgeBase.get_module_required_columns(matched_mod)

            if "mandatory" in q or "required" in q:
                return (
                    f"**Mandatory Fields for '{matched_mod}' Module ({len(req_cols)} fields):**\n\n"
                    + "\n".join([f"- `{c}`" for c in req_cols])
                )

            lines = [
                f"**SynoFin Migration Rules for '{matched_mod}' Module:**",
                f"- **Total Registered Rules:** {len(rules)}",
                f"- **Mandatory Columns:** {len(req_cols)}",
                "",
                "**Key Implemented Rules:**"
            ]
            for r in rules[:8]:
                lines.append(f"- **{r.rule_id}** (`{r.field}` | {r.severity.value if hasattr(r.severity, 'value') else r.severity}): {r.description}")
            if len(rules) > 8:
                lines.append(f"... and {len(rules) - 8} additional rules implemented in this module.")
            return "\n".join(lines)

        return None

    def _handle_concept_rule_search(self, q: str) -> Optional[str]:
        keywords = []
        if "closing balance" in q:
            keywords.append("closing_balance")
        elif "pending_amount" in q or "pending amount" in q:
            keywords.append("pending_amount")
        elif "interest rate" in q:
            keywords.append("interest_rate")
        elif "installment" in q:
            keywords.append("installment")

        if keywords:
            matches = RuleKnowledgeBase.search_rules_by_keyword(keywords[0])
            if matches:
                lines = [f"**SynoFin Validation Rules matching '{keywords[0]}':**\n"]
                for m in matches[:6]:
                    lines.append(
                        f"- **{m['rule_id']}** (Module: {m['module']}, Field: `{m['field']}` | {m['severity']}):\n"
                        f"  {m['description']}"
                    )
                return "\n".join(lines)
        return None

    def _handle_rule_explanation(self, rule_info: Dict[str, Any]) -> str:
        rule_findings = [f for f in self.context.findings if f.get("Rule ID", "").upper() == rule_info["rule_id"].upper()]
        current_finding_text = f"{len(rule_findings)} record(s) currently failing this rule in loaded audit data." if rule_findings else "No current violations for this rule in loaded data."

        return (
            f"**{rule_info['rule_id']}**\n"
            f"**Module:** {rule_info['module']}\n"
            f"**Severity:** {rule_info['severity']}\n\n"
            f"**What it checks:**\n"
            f"{rule_info['description']}\n\n"
            f"**When it applies:**\n"
            f"Evaluated on column `{rule_info['field']}` during {rule_info['module']} data migration.\n\n"
            f"**Expected condition:**\n"
            f"Values in column `{rule_info['field']}` must strictly conform to: {rule_info['description']}.\n\n"
            f"**Current finding:**\n"
            f"{current_finding_text}\n\n"
            f"**How to fix:**\n"
            f"Open your source Excel file, locate column `{rule_info['field']}`, and remediate any values that violate: {rule_info['description']}."
        )

    def _handle_loan_analysis(self, identifier: str, matched: List[Dict[str, Any]]) -> str:
        by_module: Dict[str, List[Dict[str, Any]]] = {}
        for f in matched:
            mod = f.get("Module", "General")
            by_module.setdefault(mod, []).append(f)

        lines = [
            f"**Audit Findings for Loan / Entity ID: `{identifier}`**\n",
            "**Module-wise Breakdown:**"
        ]

        for mod in ["Customer", "Loan Application", "Repayment Schedule", "Collateral"]:
            if mod in by_module:
                count = len(by_module[mod])
                lines.append(f"- **{mod}**: {count} issue(s)")
            else:
                lines.append(f"- **{mod}**: ✓ No issues")

        lines.append("\n**Detailed Finding(s):**")
        for idx, f in enumerate(matched[:6], 1):
            lines.append(
                f"{idx}. **Rule {f.get('Rule ID')}** on `{f.get('Field/Column')}` (Row {f.get('Row Number')} | {f.get('Severity')}):\n"
                f"   - Found: `{f.get('Actual Value')}`\n"
                f"   - Expected: `{f.get('Expected Value')}`\n"
                f"   - Context: {f.get('Description')}\n"
                f"   - Fix: {f.get('Remediation')}"
            )
        if len(matched) > 6:
            lines.append(f"... and {len(matched) - 6} additional findings for this loan.")
        return "\n".join(lines)

    def _handle_audit_summary(self) -> str:
        stats = self.context.get_summary_stats()
        if stats.get("mode") == "workbook":
            lines = [
                "**Audit Summary**",
                "",
                f"- **Modules / Sheets:** {stats['total_sheets']}",
                f"- **Records Audited:** {stats['total_records']}",
                f"- **Critical Errors:** {stats['total_errors']}",
                f"- **Advisory Warnings:** {stats['total_warnings']}",
                f"- **Overall Compliance Score:** {stats['compliance_score']}%",
            ]
            if "total_unique_affected_loans" in stats:
                lines.append(f"- **Distinct Affected Loans:** {stats['total_unique_affected_loans']}")
                lines.append(f"- **Loan Resolution:** {stats['resolved_affected_loans']} resolved | {stats['unresolved_findings']} unresolved findings")
            lines.extend([
                "",
                "**Module-wise Issue Summary:**"
            ])
            for s_name, s_info in stats.get("sheets", {}).items():
                if s_info["errors"] > 0 or s_info["warnings"] > 0:
                    lines.append(f"- **{s_info['module']} ({s_name})**: {s_info['errors']} errors, {s_info['warnings']} warnings ({s_info['records']} records)")
            return "\n".join(lines)
        else:
            lines = [
                "**Audit Summary**\n",
                f"- **Module:** {stats.get('module', 'Current Module')}",
                f"- **Records Audited:** {stats.get('total_records', 0)}",
                f"- **Rules Checked:** {stats.get('total_rules_checked', 0)}",
                f"- **Passed Checks:** {stats.get('total_passed', 0)}",
                f"- **Critical Errors:** {stats.get('total_errors', 0)}",
                f"- **Advisory Warnings:** {stats.get('total_warnings', 0)}",
                f"- **Compliance Score:** {stats.get('compliance_score', 0.0)}%"
            ]
            if "total_unique_affected_loans" in stats:
                lines.append(f"- **Distinct Affected Loans:** {stats['total_unique_affected_loans']}")
                lines.append(f"- **Loan Resolution:** {stats['resolved_affected_loans']} resolved | {stats['unresolved_findings']} unresolved findings")
            return "\n".join(lines)

    def _handle_audit_result_query(self, question: str) -> str:
        q = question.lower()
        if not self.context.has_audit_data():
            return "No audit results are currently available. Please upload a source Excel template or master workbook to generate an audit summary."

        total_findings = len(self.context.findings)
        if total_findings == 0:
            return "No validation findings were found in the current audit."

        stats = self.context.get_summary_stats()
        total_errors = stats.get("total_errors", sum(1 for f in self.context.findings if str(f.get("Severity", "")).upper() == "ERROR"))
        total_warnings = stats.get("total_warnings", sum(1 for f in self.context.findings if str(f.get("Severity", "")).upper() == "WARNING"))

        if ("why" in q and any(term in q for term in ["error", "issue", "fail"]) and "validation" not in q) or any(term in q for term in ["why are there errors", "why are there issues", "why this failed", "why is this failing"]):
            return self._handle_why_errors_grouped()

        if any(term in q for term in ["how many errors", "kitne errors", "error count", "count errors", "errors hain", "kritic"]):
            return f"**Current Audit Summary**\n\n**Errors:** {total_errors}\n**Warnings:** {total_warnings}\n**Total Findings:** {total_findings}"

        if any(term in q for term in ["how many warnings", "kitne warnings", "warning count", "warnings hain", "warning"]) and "error" not in q:
            return f"**Current Audit Summary**\n\n**Warnings:** {total_warnings}\n**Errors:** {total_errors}\n**Total Findings:** {total_findings}"

        if any(term in q for term in ["total findings", "kitni findings", "how many findings", "total finding", "findings count", "count findings"]):
            return f"**Current Audit Summary**\n\n**Total Findings:** {total_findings}\n**Errors:** {total_errors}\n**Warnings:** {total_warnings}"

        if any(term in q for term in ["which rules are failing", "rules are failing", "which validation rule has failures", "show failures by rule", "fail hua rule", "failed rules", "kaunsa rule sabse zyada fail hua", "which rule is failing"]):
            from collections import Counter
            rule_counts = Counter(f.get("Rule ID", "") for f in self.context.findings if f.get("Rule ID"))
            if not rule_counts:
                return "No current audit findings were found for any rules."
            lines = ["**Failing Rules in Current Audit**"]
            for rule_id, count in rule_counts.most_common():
                lines.append(f"- **{rule_id}**: {count} finding(s)")
            return "\n".join(lines)

        return self._handle_audit_summary()

    def _handle_why_errors_grouped(self) -> str:
        errors = [f for f in self.context.findings if f.get("Severity") == "ERROR"]
        if not errors:
            return "The current audit dataset has **0 critical errors**! All evaluated rules passed successfully."

        df = pd.DataFrame(errors)
        grouped = df.groupby(["Rule ID", "Field/Column", "Description"]).size().reset_index(name="count")
        grouped = grouped.sort_values(by="count", ascending=False)

        lines = [
            f"The audit identified **{len(errors)} critical error(s)** across **{len(grouped)} distinct rule category/categories**:\n"
        ]
        for _, r in grouped.head(6).iterrows():
            lines.append(
                f"- **Rule {r['Rule ID']}** on column `{r['Field/Column']}`: **{r['count']} record(s)** failed\n"
                f"  - What it checks: {r['Description']}"
            )
        if len(grouped) > 6:
            lines.append(f"\n... and {len(grouped) - 6} other rule categories affected.")
        return "\n".join(lines)

    def _handle_explain_findings(self, top_findings: List[Dict[str, Any]]) -> str:
        lines = ["**Explanation & Remediation for Current Audit Findings:**\n"]
        for idx, f in enumerate(top_findings, 1):
            lines.append(
                f"**{idx}. Rule {f.get('Rule ID')}** (`{f.get('Field/Column')}` | {f.get('Severity')}):\n"
                f"- **Context:** {f.get('Description')}\n"
                f"- **Row Number:** {f.get('Row Number')} | **Actual Value:** `{f.get('Actual Value')}`\n"
                f"- **Expected Condition:** `{f.get('Expected Value')}`\n"
                f"- **How to Fix:** {f.get('Remediation')}\n"
            )
        return "\n".join(lines)
