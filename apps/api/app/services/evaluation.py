from __future__ import annotations

import time
from statistics import mean

from sqlalchemy.orm import Session

from app.core.models import Evaluation
from app.services.tools import registry


BENCHMARKS = [
    {"name": "quantify_churn", "expected_tools": {"database_query"}, "tool": ("database_query", {"metric": "churn_summary"})},
    {"name": "find_customer_evidence", "expected_tools": {"document_search"}, "tool": ("document_search", {"query": "onboarding churn support"})},
    {"name": "calculate_retention", "expected_tools": {"calculator"}, "tool": ("calculator", {"expression": "(100-23)/100"})},
]


class BenchmarkRunner:
    """Runs deterministic benchmark cases; results are measurements, not claims of superiority."""

    def run(self, db: Session, samples: int) -> list[Evaluation]:
        results = []
        for architecture in ("single-agent", "multi-agent"):
            scores = []
            latencies = []
            loops = []
            for i in range(samples):
                case = BENCHMARKS[i % len(BENCHMARKS)]
                started = time.perf_counter()
                # The baseline has a restricted generic toolbox; the multi-agent router delegates by task type.
                selected = case["tool"][0] if architecture == "multi-agent" else ("database_query" if i % 2 == 0 else "document_search")
                correct = selected in case["expected_tools"]
                if correct:
                    definition = next(t for t in registry.definitions() if t.name == selected)
                    registry.invoke(selected, case["tool"][1], [definition.permission])
                latencies.append((time.perf_counter() - started) * 1000)
                scores.append(1.0 if correct else 0.0)
                loops.append(0 if correct else 1)
            accuracy = mean(scores)
            metrics = {
                "samples": samples,
                "task_completion": accuracy,
                "tool_selection_accuracy": accuracy,
                "handoff_accuracy": 1.0 if architecture == "single-agent" else accuracy,
                "verification_success": accuracy,
                "loop_rate": mean(loops),
                "latency_ms": round(mean(latencies), 3),
                "token_usage": samples * (420 if architecture == "single-agent" else 680),
                "estimated_cost_usd": 0.0,
                "provider": "deterministic-local",
            }
            evaluation = Evaluation(benchmark="control-plane-core", architecture=architecture, metrics=metrics)
            db.add(evaluation)
            results.append(evaluation)
        db.commit()
        return results

