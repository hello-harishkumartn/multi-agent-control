from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import Artifact, Memory


@dataclass
class ContextBundle:
    items: list[dict[str, Any]]
    token_estimate: int
    dropped: int
    policy: dict[str, Any]

    def manifest(self) -> dict[str, Any]:
        return {
            "items": [{k: v for k, v in item.items() if k != "content"} for item in self.items],
            "token_estimate": self.token_estimate,
            "dropped": self.dropped,
            "policy": self.policy,
        }


class ContextManager:
    """Retrieves, ranks, isolates, deduplicates and budgets model context."""

    @staticmethod
    def _tokens(text: str) -> int:
        return max(1, len(text) // 4)

    @staticmethod
    def _similarity(query: str, content: str) -> float:
        q = set(re.findall(r"\w+", query.lower()))
        c = set(re.findall(r"\w+", content.lower()))
        return len(q & c) / max(len(q | c), 1)

    def build(self, db: Session, *, run_id: str, agent_id: str, goal: str, policy: dict[str, Any]) -> ContextBundle:
        budget = int(policy.get("max_context_tokens", 2500))
        allowed_scopes = policy.get("memory_scopes", ["working", "task", "semantic"])
        memories = db.scalars(select(Memory).where(Memory.scope.in_(allowed_scopes))).all()
        artifacts = db.scalars(select(Artifact).where(Artifact.run_id == run_id)).all()
        candidates: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        for memory in memories:
            if memory.expires_at and memory.expires_at < now:
                continue
            # Private memory is visible only to its owning agent. Shared memory has no owner.
            if memory.owner_id and memory.owner_id != agent_id:
                continue
            score = memory.importance + self._similarity(goal, memory.content)
            created = memory.created_at.replace(tzinfo=timezone.utc) if memory.created_at.tzinfo is None else memory.created_at
            stale = (now - created).days >= int(policy.get("stale_after_days", 14))
            content = memory.content[:240] + "…" if stale and len(memory.content) > 240 else memory.content
            candidates.append({"id": memory.id, "type": f"memory:{memory.scope}", "content": content, "score": round(score, 3), "stale": stale, "summarized": stale and content != memory.content})
        for artifact in artifacts:
            content = str(artifact.content)
            candidates.append({"id": artifact.id, "type": "artifact", "content": content, "score": round(0.8 + self._similarity(goal, content), 3)})
        # Exact normalized content hash is sufficient for the deterministic demo; production uses embedding similarity.
        seen: set[str] = set()
        selected: list[dict[str, Any]] = []
        used = 0
        for item in sorted(candidates, key=lambda x: x["score"], reverse=True):
            normalized = re.sub(r"\s+", " ", item["content"].strip().lower())
            if normalized in seen:
                continue
            seen.add(normalized)
            tokens = self._tokens(item["content"])
            if used + tokens > budget:
                # Retain a bounded summary instead of silently truncating stale context.
                summary = item["content"][:240] + "…"
                tokens = self._tokens(summary)
                if used + tokens > budget:
                    continue
                item = {**item, "content": summary, "summarized": True}
            item["tokens"] = tokens
            selected.append(item)
            used += tokens
        return ContextBundle(selected, used, len(candidates) - len(selected), {**policy, "isolation": "owner-or-shared"})
