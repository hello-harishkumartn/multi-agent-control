# Memory

AgentPlane has four explicit memory scopes:

| Scope | Purpose | Typical lifetime | Sharing |
|---|---|---:|---|
| Working | Current node scratch facts | Minutes/hours | Usually private |
| Task | Evidence and handoffs for one run | Run plus retention window | Run participants |
| Episodic | Curated outcome of a completed run | Policy-defined | Restricted |
| Semantic | Stable facts, policies, and domain knowledge | Long-lived with review | Role/tenant scoped |

The runner writes structured artifacts and compact task memories; it does not copy the whole conversation. Memory records carry scope, owner, run, metadata, importance, expiry, and a native `vector(768)` embedding column. PostgreSQL starts the `vector` extension through `infra/postgres/init.sql`. The local demo uses lexical ranking so it needs no paid embedding API; production retrieval can populate that column and add an HNSW/IVFFlat index appropriate to the chosen embedding model.

Retention and promotion should be explicit jobs: expire working memory, retain task artifacts per policy, promote only evaluated outcomes to episodic memory, and admit semantic facts only after provenance and access-control review.
