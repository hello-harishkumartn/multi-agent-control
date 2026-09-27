# AgentPlane — Enterprise Agent Control Plane

AgentPlane is an open-source reference implementation for operating **multiple governed AI agents**. It is control-plane infrastructure: durable graph orchestration, agent and tool policy, explicit memory, context construction, approvals, evaluations, audit trails, and end-to-end traces—not a thin chat wrapper.

The included demo analyzes churn at a fictional SaaS company. A planner decomposes the goal; research and data agents work in parallel; an executor builds an action plan; independent reviewer and verifier agents challenge it; and a persisted human gate controls release.

## What is implemented

- Six configurable agents with identity, role, instructions, model, tools, permissions, memory/context policies, budgets, and evaluation policy
- Durable DAG runner with sequential and parallel steps, conditions, retries, fallback agents, verification, approval gates, and crash recovery
- Working, task, episodic, and semantic memory primitives with PostgreSQL/pgvector infrastructure and private-owner isolation
- Context ranking, deduplication, stale-context summarization, artifact retrieval, token budgeting, and per-step context manifests
- Permissioned tool registry, JSON schemas, risk levels, timeouts, allow-listed data access, untrusted-content envelopes, and an MCP-compatible listing adapter
- RBAC, API keys, per-agent grants, rate limiting, execution budgets, audit logs, approval gates, and environment-only secrets
- Full run traces: graph node, agent, model, context manifest, tools, latency, tokens, cost, result, and evaluation
- Deterministic local benchmark comparing single-agent and multi-agent routing without presuming a winner
- Next.js console covering Dashboard, Agents, Tools, Workflows, Runs, Memory, Evaluations, Approvals, and Analytics
- Optional Gemini and Ollama providers; the deterministic provider makes the complete demo free, offline, and reproducible

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Open the console at <http://localhost:3000>, API docs at <http://localhost:8000/docs>, and health endpoint at <http://localhost:8000/api/v1/health>. Click **Run demo**. The execution pauses at `waiting_approval`; approve it using the API:

```bash
curl http://localhost:8000/api/v1/approvals
curl -X POST http://localhost:8000/api/v1/approvals/APPROVAL_ID/decision \
  -H 'content-type: application/json' \
  -d '{"decision":"approved","comment":"Evidence reviewed"}'
```

For Gemini, set `MODEL_PROVIDER=gemini` and `GEMINI_API_KEY`, then change an agent's `model.provider` to `gemini`. For local Ollama, use `ollama`. Secrets are read from the environment and never stored in an agent record or trace.

## Tests

```bash
docker compose build api
docker compose run --rm api pip install -e '.[dev]'
docker compose run --rm api pytest -q
docker compose build web
```

The integration suite executes the whole graph through verification and human approval, plus RBAC, context isolation, benchmark, and tool-safety tests.

## Repository map

```text
apps/api/     FastAPI API, durable orchestrator, policies, tools, demo data, tests
apps/web/     Next.js operations console and trace visualization
infra/        PostgreSQL/pgvector initialization
docs/         Design decisions and operator documentation
```

## Documentation

[Architecture](docs/ARCHITECTURE.md) · [Orchestration](docs/ORCHESTRATION.md) · [Context engineering](docs/CONTEXT_ENGINEERING.md) · [Memory](docs/MEMORY.md) · [Tools](docs/TOOLS.md) · [Security](docs/SECURITY.md) · [Evaluation](docs/EVALUATION.md) · [Resume](docs/RESUME.md) · [Demo](docs/DEMO.md)

This is a production-minded reference, not a claim of production certification. See [TODO.md](TODO.md) for the hardening roadmap.
