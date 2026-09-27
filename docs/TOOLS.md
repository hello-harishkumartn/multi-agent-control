# Tools

Each tool declares name, description, JSON input/output schemas, required permission, risk level, timeout, and MCP compatibility. Agent assignment and permission grant are separate checks: an agent must have both the tool name and its permission.

Included tools are `web/mock_search`, `database_query`, `document_search`, `calculator`, `http_api_simulator`, and `file_reader`. Database access uses named aggregate queries rather than arbitrary SQL. HTTP endpoints and file roots/types are allow-listed. Arithmetic is parsed as a small AST; no `eval` is used.

External results are returned in an explicit `{trust: "untrusted", source, data}` envelope. Model system prompts state that tool results are data, never instructions. This reduces prompt-injection risk but does not replace output validation or sandboxing.

`GET /api/v1/mcp/tools` exposes MCP-style tool descriptors. The adapter is intentionally transport-neutral; production can connect those descriptors to an MCP server or import remote MCP descriptors after applying local risk and permission policy.

