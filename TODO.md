# Hardening roadmap

- [ ] Replace in-process worker threads with a leased queue and heartbeat-based recovery
- [ ] Add tenant IDs and PostgreSQL row-level security to every persisted entity
- [ ] Migrate embeddings to a native `vector(N)` column and add HNSW indexes
- [ ] Add OAuth/OIDC, short-lived service credentials, and a secrets-broker adapter
- [ ] Enforce tool timeouts and network/filesystem policy in isolated worker containers
- [ ] Add idempotency intent/outcome records for real side-effecting tools
- [ ] Version and sign workflow, prompt, policy, tool, and model configurations per run
- [ ] Add OpenTelemetry export and Prometheus metrics
- [ ] Expand benchmark corpora, model-graded rubrics with calibration, and statistical reporting
- [ ] Add visual workflow editing, schema validation, cycle detection, and draft/publish lifecycle
- [ ] Add retention jobs, memory promotion review, redaction, and right-to-delete workflows
- [ ] Add migration tooling, backup/restore drills, HA deployment examples, and SLOs

