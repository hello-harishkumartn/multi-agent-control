# Security

The reference uses layered controls:

- API-key authentication and `viewer`, `operator`, and `admin` RBAC
- Per-agent tool assignment plus permission grants
- Run token/cost budgets and per-agent budget configuration
- Request rate limiting
- Durable human approval control nodes
- Append-only-style audit events for mutations and executions
- Environment-only model secrets; keys are not persisted or traced
- Allow-listed database metrics, HTTP routes, and confined file access
- Untrusted envelopes and prompt boundaries for external tool content
- Private memory owner isolation and context manifests without copied content

The local API permits a missing API-key in development for usability. Set a non-default `API_KEY`, put TLS and identity-aware authentication at the edge, disable that convenience in a hardened deployment, and partition all records by tenant.

Before production use, run workers in isolated containers, enforce tool deadlines out-of-process, encrypt sensitive columns, connect a managed secrets broker, add row-level security, use distributed rate limits, sign audit events, add egress policy, scan artifacts, and threat-model every new tool.

