# Evaluation

Evaluation is a control-plane concern, not a final prompt. AgentPlane records per-step policy scores and run-level measurements: task completion, tool-selection accuracy, handoff accuracy, verification success, loop rate, latency, token use, and estimated cost.

`POST /api/v1/evaluations/benchmark` executes deterministic benchmark cases for both architectures. The single-agent baseline uses a generic routing rule; the multi-agent path uses role routing. Results are persisted with sample count and provider. These are actual local harness results, but they measure this small synthetic suite only—they do not prove that multi-agent design is generally superior.

For meaningful comparison, expand the corpus, freeze versions, run both architectures on identical cases and model settings, repeat samples, report confidence intervals, and include failure severity. Multi-agent wins only when quality or governance gains justify added latency, tokens, coordination failures, and operational complexity.

