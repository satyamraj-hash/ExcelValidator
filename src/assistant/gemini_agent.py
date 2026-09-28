import json
import os
from typing import Any, Dict, List, Optional

DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
GEMINI_UNAVAILABLE_MESSAGE = (
    "Gemini is not configured. I can still answer using the migration knowledge and audit tools."
)


class GeminiToolCall:
    """Container for a parsed Gemini function call."""

    def __init__(self, name: str, arguments: Optional[Dict[str, Any]] = None):
        self.name = name
        self.arguments = arguments or {}


class GeminiAgent:
    """Gemini agent layer that routes to existing deterministic Python tools."""

    TOOL_DEFINITIONS = [
        {
            "name": "search_template",
            "description": "Retrieve workbook template-defined columns, meanings, allowed values, or relationships using the deterministic template knowledge service.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_validation_rules",
            "description": "Retrieve validation rules from the existing RuleKnowledgeBase for a module or a specific rule ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                },
                "required": ["question"],
            },
        },
        {
            "name": "get_loan_findings",
            "description": "Get actual validation findings for a specific loan or application number from the current audit context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "loan_id": {"type": "string"},
                    "question": {"type": "string"},
                },
                "required": ["loan_id"],
            },
        },
        {
            "name": "get_loan_data",
            "description": "Retrieve supported cross-sheet data for a specific loan using existing template relationships and current workbook/session data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "loan_id": {"type": "string"},
                    "question": {"type": "string"},
                },
                "required": ["loan_id"],
            },
        },
        {
            "name": "run_reconciliation",
            "description": "Run the existing supported reconciliation using current workbook/session data. Never invent a reconciliation rule or amount.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "loan_id": {"type": "string"},
                },
                "required": ["question"],
            },
        },
    ]

    def __init__(self, assistant: Optional[Any] = None, context: Optional[Any] = None, history: Optional[List[str]] = None):
        self.assistant = assistant
        self.context = context
        self.model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.history = list(history or [])
        self.max_tool_calls = 2

    def is_configured(self) -> bool:
        return bool(self.api_key and str(self.api_key).strip())

    @staticmethod
    def _fallback_response() -> str:
        return GEMINI_UNAVAILABLE_MESSAGE

    @staticmethod
    def _safe_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False, default=str)
        return str(value)

    def build_system_instruction(self) -> str:
        return (
            "You are an assistant for SynoFin LMS migration analysis. "
            "Python tool results are authoritative. Deterministic Python tools are the authoritative source of truth. "
            "Never invent or guess validation rules, column definitions, allowed values, sheet relationships, loan data, audit findings, reconciliation results, amounts, or counts. "
            "If a tool does not provide the information, say that it is not available. "
            "Do not perform your own validation or reconciliation when a deterministic tool exists. "
            "Do not override a tool result. Keep the final answer concise, factual, and grounded in the current session data."
        )

    def tool_definitions(self) -> List[Dict[str, Any]]:
        return [dict(tool) for tool in self.TOOL_DEFINITIONS]

    def select_tool(self, question: str) -> str:
        q = question.lower()
        if "how do i link" in q or "link loan records across sheets" in q or "relationship" in q or "link across sheets" in q or "sheets kaise connected" in q or "connected" in q:
            return "search_template"
        if any(token in q for token in ["validation", "rule", "severity", "what does rule", "which rules", "repayment schedule", "validations are applied", "rps-009", "kya hai?"]):
            return "get_validation_rules"
        if any(token in q for token in ["issue", "issues", "finding", "findings", "errors", "warnings", "problem", "failed", "why did", "what happened", "kya galat", "loan mein kya galat", "complete investigation"]):
            return "get_loan_findings"
        if any(token in q for token in ["compare", "reconciliation", "mismatch", "show reconciliation", "compare receipts", "compare charges", "receipts aur repayment", "compare karo"]):
            return "run_reconciliation"
        if any(token in q for token in ["customer", "bank details", "bank detail", "nach", "repayment", "charges", "receipts", "show data", "ka bank", "bank detail bata", "customer ka naam", "loan data"]):
            return "get_loan_data"
        return "search_template"

    def execute_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = arguments or {}
        tool_name = str(tool_name or "").strip()
        if tool_name == "search_template":
            query = str(args.get("query") or args.get("question") or "").strip()
            if not self.assistant:
                return {"tool": "search_template", "query": query, "result": "This information is not defined in the migration template."}
            result = self.assistant._handle_template_query(query or "template relationship")
            return {"tool": "search_template", "query": query, "result": result or "This information is not defined in the migration template."}
        if tool_name == "get_validation_rules":
            question = str(args.get("question") or args.get("query") or "").strip() or ""
            if not self.assistant:
                return {"tool": "get_validation_rules", "result": "No validation-rule metadata is available in the current session."}
            result = self.assistant._handle_validation_registry_query(question)
            return {"tool": "get_validation_rules", "question": question, "result": result or "No validation-rule metadata is available in the current session."}
        if tool_name == "get_loan_findings":
            loan_id = str(args.get("loan_id") or "").strip()
            question = str(args.get("question") or "").strip()
            if not loan_id and self.assistant:
                loan_id = self.assistant._extract_loan_identifier(question)
            if not self.assistant or not loan_id:
                return {"tool": "get_loan_findings", "loan_id": loan_id, "result": "No loan identifier was found in the current session."}
            result = self.assistant._handle_loan_investigation_query(loan_id, question or f"show issues for loan {loan_id}")
            return {"tool": "get_loan_findings", "loan_id": loan_id, "result": result}
        if tool_name == "get_loan_data":
            loan_id = str(args.get("loan_id") or "").strip()
            question = str(args.get("question") or "").strip()
            if not self.assistant or not loan_id:
                return {"tool": "get_loan_data", "loan_id": loan_id, "result": "No loan identifier was found in the current workbook data."}
            result = self.assistant._handle_cross_sheet_lookup(question or f"Show data for loan {loan_id} across all sheets.", loan_id)
            return {"tool": "get_loan_data", "loan_id": loan_id, "result": result}
        if tool_name == "run_reconciliation":
            question = str(args.get("question") or "").strip()
            if not self.assistant:
                return {"tool": "run_reconciliation", "result": "Reconciliation rule not defined in current template/business rules."}
            result = self.assistant._handle_reconciliation_question(question)
            return {"tool": "run_reconciliation", "question": question, "result": result}
        return {"tool": tool_name, "result": "This information is not available in the current deterministic tool layer."}

    def _parse_function_call(self, response: Any) -> Optional[GeminiToolCall]:
        if not response:
            return None

        candidates = getattr(response, "candidates", None)
        if candidates:
            for candidate in candidates:
                content = getattr(candidate, "content", None)
                parts = getattr(content, "parts", None) or []
                for part in parts:
                    func = getattr(part, "function_call", None)
                    if func is not None:
                        name = getattr(func, "name", None) or getattr(func, "function_name", None) or ""
                        args = getattr(func, "args", None) or getattr(func, "arguments", None) or {}
                        if isinstance(args, dict):
                            return GeminiToolCall(str(name), args)
                        if hasattr(args, "__dict__"):
                            return GeminiToolCall(str(name), dict(args.__dict__))
                if hasattr(candidate, "function_call"):
                    func = candidate.function_call
                    name = getattr(func, "name", None) or getattr(func, "function_name", None) or ""
                    args = getattr(func, "args", None) or getattr(func, "arguments", None) or {}
                    if isinstance(args, dict):
                        return GeminiToolCall(str(name), args)
        if isinstance(response, dict):
            function_call = response.get("function_call") or response.get("tool_call") or response.get("toolCall")
            if function_call:
                name = function_call.get("name") or function_call.get("function_name") or ""
                args = function_call.get("arguments") or function_call.get("args") or {}
                return GeminiToolCall(str(name), args if isinstance(args, dict) else {})
        if hasattr(response, "function_call"):
            func = response.function_call
            if func is not None:
                name = getattr(func, "name", None) or getattr(func, "function_name", None) or ""
                args = getattr(func, "args", None) or getattr(func, "arguments", None) or {}
                return GeminiToolCall(str(name), args if isinstance(args, dict) else {})
        return None

    def _generate_from_api(self, prompt: str, *args: Any, **kwargs: Any) -> Any:
        if not self.is_configured():
            return self._fallback_response()

        tool_definitions = kwargs.get("tool_definitions") or kwargs.get("tools")
        if args:
            maybe_tool_definitions = args[0]
            if isinstance(maybe_tool_definitions, list):
                tool_definitions = maybe_tool_definitions

        try:
            import google.generativeai as genai  # type: ignore
        except ImportError:
            try:
                from google import genai  # type: ignore
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise RuntimeError("Gemini SDK is not installed.") from exc
            client = genai.Client(api_key=self.api_key)
            if tool_definitions:
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={"tools": tool_definitions},
                )
            else:
                response = client.models.generate_content(model=self.model, contents=prompt)
            return response

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)
        if tool_definitions:
            response = model.generate_content(prompt, tools=tool_definitions)
        else:
            response = model.generate_content(prompt)
        return response

    @staticmethod
    def _extract_text(response: Any) -> str:
        if response is None:
            return ""
        if hasattr(response, "text") and response.text:
            return str(response.text)
        if isinstance(response, dict):
            text = response.get("text") or response.get("content") or ""
            if text:
                return str(text)
            return json.dumps(response, ensure_ascii=False)
        if hasattr(response, "candidates"):
            parts: List[str] = []
            for candidate in response.candidates:
                if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                    for part in candidate.content.parts:
                        if hasattr(part, "text"):
                            parts.append(str(part.text))
            if parts:
                return "\n".join(parts)
        try:
            return str(response)
        except Exception:
            return ""

    def _tool_call_prompt(self, question: str) -> str:
        return json.dumps(
            {
                "system_instruction": self.build_system_instruction(),
                "question": question,
                "history": self.history[-4:],
                "tool_definitions": self.tool_definitions(),
            },
            ensure_ascii=False,
        )

    def _final_answer_prompt(self, question: str, tool_name: str, tool_result: Dict[str, Any]) -> str:
        return json.dumps(
            {
                "system_instruction": self.build_system_instruction(),
                "question": question,
                "history": self.history[-4:],
                "tool_used": tool_name,
                "tool_result": tool_result,
            },
            ensure_ascii=False,
        )

    def answer(self, question: str, context: Optional[Any] = None, history: Optional[List[str]] = None) -> str:
        if not question or not str(question).strip():
            return "Please ask a question about migration rules, audit findings, or workbook data."

        if not self.is_configured():
            return self._fallback_response()

        if context is not None:
            self.context = context
        if history is not None:
            self.history = list(history)

        tool_name = self.select_tool(question)
        deterministic = self.execute_tool(tool_name, {"question": question})
        prompt = json.dumps(
            {
                "system_instruction": self.build_system_instruction(),
                "question": question,
                "history": self.history[-4:],
                "tool": tool_name,
                "tool_names": [tool_name],
                "tool_definitions": self.tool_definitions(),
                "tool_result": deterministic.get("result"),
                "context_summary": self._safe_text(getattr(self.context, "module_name", "")),
            },
            ensure_ascii=False,
        )

        try:
            raw_response = self._generate_from_api(prompt)
        except Exception:
            deterministic = self.execute_tool(tool_name, {"question": question})
            return self._safe_text(deterministic.get("result", self._fallback_response()))

        tool_call = self._parse_function_call(raw_response)
        if tool_call and tool_call.name:
            tool_result = self.execute_tool(tool_call.name, tool_call.arguments)
            final_prompt = self._final_answer_prompt(question, tool_call.name, tool_result)
            try:
                final_response = self._generate_from_api(final_prompt)
            except Exception:
                return self._safe_text(tool_result.get("result", "No result was available."))
            cleaned = self._extract_text(final_response).strip()
            if cleaned:
                return cleaned
            return self._safe_text(tool_result.get("result", "No result was available."))

        if tool_name:
            deterministic = self.execute_tool(tool_name, {"question": question})
            if deterministic.get("result"):
                return self._safe_text(deterministic.get("result"))

        return self._safe_text(self._extract_text(raw_response) or self._fallback_response())
