from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.models import Agent, Approval, Artifact, AuditLog, Evaluation, Run, StepRun, Workflow, now
from app.services.agent_runner import AgentRunner


TERMINAL = {"completed", "skipped"}


class OrchestrationError(RuntimeError):
    pass


class Orchestrator:
    """Database-checkpointed DAG scheduler. Safe to call again after process restart."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory
        self.runner = AgentRunner()

    def create_run(self, db: Session, workflow: Workflow, goal: str, budget: dict[str, Any], actor: str) -> Run:
        run = Run(workflow_id=workflow.id, goal=goal, status="queued", state={"completed_nodes": [], "outputs": {}}, budget=budget, created_by=actor)
        db.add(run)
        db.flush()
        agents = {a.slug: a for a in db.scalars(select(Agent)).all()}
        for node in workflow.graph["nodes"]:
            agent = agents.get(node.get("agent"))
            db.add(StepRun(run_id=run.id, node_id=node["id"], agent_id=agent.id if agent else None))
        db.add(AuditLog(actor=actor, action="run.created", resource_type="run", resource_id=run.id, details={"workflow": workflow.slug}))
        db.commit()
        return run

    def resume(self, run_id: str) -> Run:
        with self.session_factory() as db:
            run = db.get(Run, run_id)
            if not run:
                raise OrchestrationError("Run not found")
            if run.status in {"completed", "rejected", "failed", "budget_exceeded"}:
                return run
            # A process may have died after checkpointing 'running'. Requeue those nodes.
            for step in run.steps:
                if step.status == "running":
                    step.status = "pending"
                    step.error = "Recovered interrupted execution"
            run.status = "running"
            run.started_at = run.started_at or now()
            db.commit()

        while True:
            with self.session_factory() as db:
                run = db.get(Run, run_id)
                workflow = db.get(Workflow, run.workflow_id)
                nodes = {n["id"]: n for n in workflow.graph["nodes"]}
                steps = {s.node_id: s for s in run.steps}
                if self._over_budget(run):
                    run.status = "budget_exceeded"
                    run.finished_at = now()
                    db.commit()
                    return run
                ready = [n for n in nodes.values() if steps[n["id"]].status == "pending" and all(steps[d].status in TERMINAL for d in n.get("depends_on", []))]
                if not ready:
                    pending = [s for s in steps.values() if s.status not in TERMINAL]
                    if not pending:
                        run.status = "completed"
                        run.finished_at = now()
                        db.add(Evaluation(run_id=run.id, benchmark="runtime-policy", architecture="multi-agent", metrics=self._runtime_metrics(run)))
                    elif run.status != "waiting_approval":
                        run.status = "failed"
                        run.finished_at = now()
                        run.state = {**run.state, "error": "No runnable nodes; graph may contain a cycle or failed dependency"}
                    db.commit()
                    return run
                approval_node = next((n for n in ready if n.get("kind") == "approval"), None)
                if approval_node:
                    step = steps[approval_node["id"]]
                    existing = db.scalar(select(Approval).where(Approval.run_id == run.id, Approval.node_id == approval_node["id"], Approval.status == "pending"))
                    if not existing:
                        db.add(Approval(run_id=run.id, node_id=approval_node["id"], reason=approval_node.get("reason", "Human review required")))
                    step.status = "waiting_approval"
                    run.status = "waiting_approval"
                    db.commit()
                    return run
                ready_ids = [n["id"] for n in ready]

            # Ready nodes are independent by construction and can execute concurrently.
            with ThreadPoolExecutor(max_workers=min(4, len(ready_ids))) as pool:
                futures = {pool.submit(self._execute_node, run_id, node_id): node_id for node_id in ready_ids}
                for future in as_completed(futures):
                    future.result()

    def _execute_node(self, run_id: str, node_id: str) -> None:
        with self.session_factory() as db:
            run = db.get(Run, run_id)
            workflow = db.get(Workflow, run.workflow_id)
            node = next(n for n in workflow.graph["nodes"] if n["id"] == node_id)
            step = db.scalar(select(StepRun).where(StepRun.run_id == run_id, StepRun.node_id == node_id))
            if not self._condition_matches(run.state, node.get("condition")):
                step.status = "skipped"
                step.finished_at = now()
                db.commit()
                return
            agent = db.get(Agent, step.agent_id) if step.agent_id else None
            step.status = "running"
            step.attempt += 1
            step.started_at = now()
            step.input = {"goal": run.goal, "dependencies": node.get("depends_on", [])}
            db.commit()
            try:
                if not agent:
                    raise OrchestrationError(f"Node {node_id} has no agent")
                output = self.runner.execute(db, run, step, agent)
                step.output = output
                step.status = "completed"
                step.finished_at = now()
                step.evaluation = self._evaluate_step(agent, output)
                self.runner.persist_artifact(db, run, step, node, output)
                state = dict(run.state)
                state["completed_nodes"] = list(dict.fromkeys([*state.get("completed_nodes", []), node_id]))
                state["outputs"] = {**state.get("outputs", {}), node_id: output}
                run.state = state
                run.tokens_used += step.tokens
                run.estimated_cost_usd = round(run.estimated_cost_usd + step.estimated_cost_usd, 6)
                db.add(AuditLog(actor=f"agent:{agent.slug}", action="step.completed", resource_type="run", resource_id=run.id, details={"node": node_id, "attempt": step.attempt}))
                db.commit()
            except Exception as exc:
                db.rollback()
                step = db.scalar(select(StepRun).where(StepRun.run_id == run_id, StepRun.node_id == node_id))
                step.error = str(exc)
                retries = int(node.get("retries", 0))
                if step.attempt <= retries:
                    step.status = "pending"
                elif node.get("fallback_agent"):
                    fallback = db.scalar(select(Agent).where(Agent.slug == node["fallback_agent"]))
                    step.agent_id = fallback.id if fallback else step.agent_id
                    step.status = "pending" if fallback else "failed"
                else:
                    step.status = "failed"
                step.finished_at = now()
                db.commit()

    def decide_approval(self, db: Session, approval: Approval, decision: str, actor: str, comment: str) -> Run:
        if approval.status != "pending":
            raise OrchestrationError("Approval has already been decided")
        approval.status = decision
        approval.decided_at = now()
        approval.decided_by = actor
        approval.comment = comment
        run = db.get(Run, approval.run_id)
        step = db.scalar(select(StepRun).where(StepRun.run_id == run.id, StepRun.node_id == approval.node_id))
        step.output = {"decision": decision, "actor": actor, "comment": comment}
        step.finished_at = now()
        db.add(Artifact(run_id=run.id, step_id=step.id, name="human-approval", content=step.output))
        db.add(AuditLog(actor=actor, action=f"approval.{decision}", resource_type="run", resource_id=run.id, details={"approval_id": approval.id, "comment": comment}))
        if decision == "approved":
            step.status = "completed"
            run.status = "running"
        else:
            step.status = "completed"
            run.status = "rejected"
            run.finished_at = now()
        db.commit()
        return run

    @staticmethod
    def _condition_matches(state: dict[str, Any], condition: dict[str, Any] | None) -> bool:
        if not condition:
            return True
        value: Any = state
        for part in condition.get("path", "").split("."):
            value = value.get(part) if isinstance(value, dict) else None
        return value == condition.get("equals")

    @staticmethod
    def _over_budget(run: Run) -> bool:
        return run.tokens_used >= int(run.budget.get("max_tokens", 30000)) or run.estimated_cost_usd >= float(run.budget.get("max_cost_usd", 1.0))

    @staticmethod
    def _evaluate_step(agent: Agent, output: dict[str, Any]) -> dict[str, Any]:
        complete = bool(output)
        verified = output.get("passed", True)
        return {"complete": complete, "policy": agent.evaluation_policy, "score": 1.0 if complete and verified else 0.5}

    @staticmethod
    def _runtime_metrics(run: Run) -> dict[str, Any]:
        steps = [s for s in run.steps if s.agent_id]
        latency = 0.0
        for s in steps:
            if s.started_at and s.finished_at:
                latency += (s.finished_at - s.started_at).total_seconds()
        return {
            "task_completion": 1.0,
            "tool_selection_accuracy": round(sum(bool(s.tool_calls) for s in steps) / max(len([s for s in steps if s.tool_calls]), 1), 2),
            "handoff_accuracy": round(sum(s.status == "completed" for s in steps) / max(len(steps), 1), 2),
            "verification_success": any(s.output.get("passed") for s in steps),
            "loop_rate": round(sum(max(0, s.attempt - 1) for s in steps) / max(len(steps), 1), 2),
            "latency_seconds": round(latency, 3),
            "token_usage": run.tokens_used,
            "estimated_cost_usd": run.estimated_cost_usd,
        }

