import pytest

from src.assistant.gemini_agent import GeminiAgent, GEMINI_UNAVAILABLE_MESSAGE
from src.assistant.service import AuditAssistant


def test_gemini_config_default_model(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    agent = GeminiAgent()
    assert not agent.is_configured()
    assert agent.model == "gemini-1.5-flash"


def test_gemini_agent_falls_back_when_unconfigured(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    agent = GeminiAgent(assistant=AuditAssistant())
    response = agent.answer("How do I link loan records across sheets?")
    assert GEMINI_UNAVAILABLE_MESSAGE in response


def test_gemini_agent_uses_deterministic_tool_result_and_system_instruction(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assistant = AuditAssistant()
    agent = GeminiAgent(assistant=assistant, context=assistant.context)

    captured = {}

    def fake_generate(prompt):
        captured["prompt"] = prompt
        return "loan_application_number is the linking key across the workbook."

    monkeypatch.setattr(agent, "_generate_from_api", fake_generate)

    response = agent.answer("How do I link loan records across sheets?")

    assert "loan_application_number" in response.lower()
    assert "Python tool results are authoritative" in captured["prompt"]
    assert "tool_result" in captured["prompt"]


def test_gemini_agent_falls_back_to_deterministic_result_when_api_errors(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assistant = AuditAssistant()
    agent = GeminiAgent(assistant=assistant, context=assistant.context)

    def fake_fail(prompt):
        raise RuntimeError("API timeout")

    monkeypatch.setattr(agent, "_generate_from_api", fake_fail)

    response = agent.answer("How do I link loan records across sheets?")
    assert "loan_application_number" in response.lower()
    assert "linking key" in response.lower()
