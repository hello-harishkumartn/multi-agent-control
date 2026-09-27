import pytest

from app.services.tools import ToolError, registry


def test_calculator_rejects_code_execution():
    with pytest.raises((ToolError, SyntaxError)):
        registry.invoke("calculator", {"expression": "__import__('os').system('echo nope')"}, ["tool:calculator"])


def test_tool_permission_is_enforced():
    with pytest.raises(ToolError, match="lacks"):
        registry.invoke("database_query", {"metric": "churn_summary"}, [])


def test_database_tool_only_accepts_allowlisted_metrics():
    with pytest.raises(ToolError, match="allow-listed"):
        registry.invoke("database_query", {"metric": "DROP TABLE customers"}, ["tool:database_query"])

