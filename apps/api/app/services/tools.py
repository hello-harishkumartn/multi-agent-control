from __future__ import annotations

import ast
import csv
import operator
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from app.core.config import get_settings
from app.core.security import tool_allowed


class ToolError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    permission: str
    risk_level: str
    timeout_seconds: int
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    mcp_compatible: bool = True


def _untrusted(data: Any, source: str) -> dict[str, Any]:
    """Mark external content so prompts never confuse it with instructions."""
    return {"trust": "untrusted", "source": source, "data": data}


def calculator(args: dict[str, Any]) -> dict[str, Any]:
    operations = {
        ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg,
    }

    def evaluate(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            return operations[type(node.op)](evaluate(node.left), evaluate(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in operations:
            return operations[type(node.op)](evaluate(node.operand))
        raise ToolError("Only numeric arithmetic is allowed")

    expression = str(args.get("expression", ""))
    if len(expression) > 200:
        raise ToolError("Expression too long")
    return {"result": evaluate(ast.parse(expression, mode="eval").body)}


def database_query(args: dict[str, Any]) -> dict[str, Any]:
    """A deliberately allow-listed analytics interface, not raw SQL execution."""
    rows = list(csv.DictReader((get_settings().data_dir / "customers.csv").open(encoding="utf-8")))
    metric = args.get("metric", "churn_summary")
    if metric == "churn_summary":
        total = len(rows)
        churned = sum(r["churned"] == "true" for r in rows)
        by_plan: dict[str, dict[str, int | float]] = {}
        by_segment: dict[str, dict[str, int | float]] = {}
        for row in rows:
            for key, target in (("plan", by_plan), ("segment", by_segment)):
                bucket = target.setdefault(row[key], {"customers": 0, "churned": 0})
                bucket["customers"] += 1
                bucket["churned"] += row["churned"] == "true"
        for group in (by_plan, by_segment):
            for value in group.values():
                value["churn_rate"] = round(value["churned"] / value["customers"], 3)
        return {"customers": total, "churned": churned, "churn_rate": round(churned / total, 3), "by_plan": by_plan, "by_segment": by_segment}
    if metric == "risk_factors":
        churned = [r for r in rows if r["churned"] == "true"]
        active = [r for r in rows if r["churned"] == "false"]
        avg = lambda xs, key: round(sum(float(r[key]) for r in xs) / max(len(xs), 1), 2)
        return {
            "churned": {"avg_tickets": avg(churned, "support_tickets"), "avg_logins": avg(churned, "monthly_logins"), "avg_nps": avg(churned, "nps")},
            "retained": {"avg_tickets": avg(active, "support_tickets"), "avg_logins": avg(active, "monthly_logins"), "avg_nps": avg(active, "nps")},
        }
    raise ToolError(f"Metric is not allow-listed: {metric}")


def document_search(args: dict[str, Any]) -> dict[str, Any]:
    query_terms = set(re.findall(r"[a-z]+", str(args.get("query", "")).lower()))
    documents = []
    for path in (get_settings().data_dir / "reports").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        score = len(query_terms & set(re.findall(r"[a-z]+", text.lower())))
        if score:
            documents.append({"title": path.stem.replace("_", " ").title(), "excerpt": text[:800], "score": score})
    return _untrusted(sorted(documents, key=lambda d: d["score"], reverse=True)[:5], "internal_document_index")


def mock_search(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query", "customer retention"))
    results = [
        {"title": "Retention playbook", "snippet": "Segment interventions by churn risk and measure incremental retention."},
        {"title": "Onboarding study", "snippet": "Early activation and time-to-value are leading retention indicators."},
    ]
    return _untrusted({"query": query, "results": results}, "mock_search")


def http_simulator(args: dict[str, Any]) -> dict[str, Any]:
    allowed = {"crm/customer-health", "billing/plan-summary"}
    endpoint = str(args.get("endpoint", ""))
    if endpoint not in allowed:
        raise ToolError("Endpoint is not allow-listed")
    return _untrusted({"endpoint": endpoint, "status": 200, "request_id": "sim-001"}, "http_simulator")


def file_reader(args: dict[str, Any]) -> dict[str, Any]:
    root = get_settings().data_dir.resolve()
    requested = (root / str(args.get("path", ""))).resolve()
    if root not in requested.parents or requested.suffix not in {".md", ".csv", ".json"}:
        raise ToolError("File path or type is not allowed")
    return _untrusted(requested.read_text(encoding="utf-8")[:20_000], "file_reader")


class ToolRegistry:
    def __init__(self) -> None:
        obj = {"type": "object"}
        self._tools = {
            item.name: item for item in [
                ToolDefinition("calculator", "Evaluate safe arithmetic", {**obj, "properties": {"expression": {"type": "string"}}}, obj, "tool:calculator", "low", 2, calculator),
                ToolDefinition("database_query", "Query allow-listed synthetic customer metrics", {**obj, "properties": {"metric": {"enum": ["churn_summary", "risk_factors"]}}}, obj, "tool:database_query", "medium", 10, database_query),
                ToolDefinition("document_search", "Search synthetic internal reports", {**obj, "properties": {"query": {"type": "string"}}}, obj, "tool:document_search", "low", 10, document_search),
                ToolDefinition("web/mock_search", "Search a deterministic mock web index", {**obj, "properties": {"query": {"type": "string"}}}, obj, "tool:web/mock_search", "low", 10, mock_search),
                ToolDefinition("http_api_simulator", "Call an allow-listed simulated API", {**obj, "properties": {"endpoint": {"type": "string"}}}, obj, "tool:http_api_simulator", "high", 10, http_simulator),
                ToolDefinition("file_reader", "Read a safe file under the demo data root", {**obj, "properties": {"path": {"type": "string"}}}, obj, "tool:file_reader", "medium", 5, file_reader),
            ]
        }

    def definitions(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def invoke(self, name: str, arguments: dict[str, Any], permissions: list[str]) -> dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            raise ToolError(f"Unknown tool: {name}")
        if not tool_allowed(permissions, tool.permission):
            raise ToolError(f"Agent lacks {tool.permission}")
        pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"tool-{name}")
        future = pool.submit(tool.handler, arguments)
        try:
            return future.result(timeout=tool.timeout_seconds)
        except FutureTimeout as exc:
            future.cancel()
            raise ToolError(f"Tool timed out after {tool.timeout_seconds}s") from exc
        finally:
            # A production worker should terminate timed-out calls out-of-process.
            pool.shutdown(wait=False, cancel_futures=True)


registry = ToolRegistry()


class MCPAdapter:
    """Small translation layer for exposing registry definitions as MCP-style tools."""

    @staticmethod
    def list_tools() -> list[dict[str, Any]]:
        return [{"name": t.name, "description": t.description, "inputSchema": t.input_schema} for t in registry.definitions() if t.mcp_compatible]
