from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import SessionLocal, get_db
from app.core.models import Agent, Approval, Artifact, AuditLog, Evaluation, Memory, Run, StepRun, Tool, Workflow
from app.core.schemas import AgentCreate, ApprovalDecision, BenchmarkRequest, MemoryCreate, RunCreate, ToolInvoke, WorkflowCreate
from app.core.security import Principal, require
from app.services.evaluation import BenchmarkRunner
from app.services.orchestrator import OrchestrationError, Orchestrator
from app.services.tools import ToolError, registry


router = APIRouter(prefix="/api/v1")
orchestrator = Orchestrator(SessionLocal)


def serialize_agent(a: Agent) -> dict:
    return {key: getattr(a, key) for key in ("id", "slug", "name", "identity", "role", "instructions", "model", "tools", "permissions", "memory_config", "context_policy", "budget", "evaluation_policy", "enabled")}


def serialize_run(run: Run, detail: bool = False) -> dict:
    data = {key: getattr(run, key) for key in ("id", "workflow_id", "goal", "status", "state", "budget", "tokens_used", "estimated_cost_usd", "started_at", "finished_at", "created_at")}
    if detail:
        data["steps"] = [{key: getattr(s, key) for key in ("id", "node_id", "agent_id", "status", "attempt", "input", "output", "context_manifest", "tool_calls", "model_info", "evaluation", "tokens", "estimated_cost_usd", "error", "started_at", "finished_at")} for s in sorted(run.steps, key=lambda x: x.started_at or run.created_at)]
    return data


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _: Principal = Depends(require("read"))) -> dict:
    runs = db.scalars(select(Run).order_by(desc(Run.created_at)).limit(8)).all()
    pending = db.scalar(select(func.count()).select_from(Approval).where(Approval.status == "pending")) or 0
    active_agents = db.scalar(select(func.count()).select_from(Agent).where(Agent.enabled)) or 0
    completed = [r for r in runs if r.status == "completed"]
    return {
        "counts": {"agents": active_agents, "runs": db.scalar(select(func.count()).select_from(Run)) or 0, "pending_approvals": pending, "workflows": db.scalar(select(func.count()).select_from(Workflow)) or 0},
        "recent_runs": [serialize_run(r) for r in runs],
        "metrics": {"completion_rate": round(len(completed) / max(len(runs), 1), 2), "tokens": sum(r.tokens_used for r in runs), "cost_usd": round(sum(r.estimated_cost_usd for r in runs), 4)},
    }


@router.get("/agents")
def list_agents(db: Session = Depends(get_db), _: Principal = Depends(require("read"))) -> list[dict]:
    return [serialize_agent(a) for a in db.scalars(select(Agent).order_by(Agent.name)).all()]


@router.post("/agents", status_code=201)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db), principal: Principal = Depends(require("*"))) -> dict:
    agent = Agent(**payload.model_dump())
    db.add(agent); db.flush()
    db.add(AuditLog(actor=principal.name, action="agent.created", resource_type="agent", resource_id=agent.id, details={"slug": agent.slug}))
    db.commit(); db.refresh(agent)
    return serialize_agent(agent)


@router.get("/tools", response_model=None)
def list_tools(db: Session = Depends(get_db), _: Principal = Depends(require("read"))) -> list[Tool]:
    return list(db.scalars(select(Tool).order_by(Tool.name)).all())


@router.post("/tools/{tool_name}/invoke")
def invoke_tool(tool_name: str, payload: ToolInvoke, db: Session = Depends(get_db), principal: Principal = Depends(require("tool:invoke"))) -> dict:
    try:
        result = registry.invoke(tool_name, payload.arguments, ["tool:*"])
    except ToolError as exc:
        raise HTTPException(400, str(exc)) from exc
    db.add(AuditLog(actor=principal.name, action="tool.invoked", resource_type="tool", resource_id=tool_name, details={"arguments": payload.arguments}))
    db.commit()
    return result


@router.get("/mcp/tools")
def mcp_tools(_: Principal = Depends(require("read"))) -> dict:
    from app.services.tools import MCPAdapter
    return {"tools": MCPAdapter.list_tools()}


@router.get("/workflows", response_model=None)
def list_workflows(db: Session = Depends(get_db), _: Principal = Depends(require("read"))) -> list[Workflow]:
    return list(db.scalars(select(Workflow).order_by(Workflow.name)).all())


@router.post("/workflows", status_code=201, response_model=None)
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db), principal: Principal = Depends(require("*"))) -> Workflow:
    node_ids = [n.get("id") for n in payload.graph.get("nodes", [])]
    if not node_ids or len(node_ids) != len(set(node_ids)):
        raise HTTPException(400, "Workflow nodes must have unique IDs")
    workflow = Workflow(**payload.model_dump())
    db.add(workflow); db.flush()
    db.add(AuditLog(actor=principal.name, action="workflow.created", resource_type="workflow", resource_id=workflow.id, details={"slug": workflow.slug}))
    db.commit(); db.refresh(workflow)
    return workflow


@router.get("/runs")
def list_runs(db: Session = Depends(get_db), _: Principal = Depends(require("read"))) -> list[dict]:
    return [serialize_run(r) for r in db.scalars(select(Run).order_by(desc(Run.created_at))).all()]


@router.get("/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db), _: Principal = Depends(require("read"))) -> dict:
    run = db.scalar(select(Run).options(selectinload(Run.steps)).where(Run.id == run_id))
    if not run: raise HTTPException(404, "Run not found")
    data = serialize_run(run, True)
    data["artifacts"] = [{"id": a.id, "name": a.name, "content": a.content, "media_type": a.media_type, "created_at": a.created_at} for a in db.scalars(select(Artifact).where(Artifact.run_id == run_id)).all()]
    return data


@router.post("/runs", status_code=202)
def create_run(payload: RunCreate, background: BackgroundTasks, db: Session = Depends(get_db), principal: Principal = Depends(require("run:create"))) -> dict:
    workflow = db.get(Workflow, payload.workflow_id) if payload.workflow_id else db.scalar(select(Workflow).where(Workflow.slug == payload.workflow_slug))
    if not workflow: raise HTTPException(404, "Workflow not found")
    run = orchestrator.create_run(db, workflow, payload.goal, payload.budget, principal.name)
    background.add_task(orchestrator.resume, run.id)
    return serialize_run(run)


@router.post("/runs/{run_id}/resume", status_code=202)
def resume_run(run_id: str, background: BackgroundTasks, db: Session = Depends(get_db), _: Principal = Depends(require("run:create"))) -> dict:
    if not db.get(Run, run_id): raise HTTPException(404, "Run not found")
    background.add_task(orchestrator.resume, run_id)
    return {"run_id": run_id, "status": "resuming"}


@router.get("/approvals", response_model=None)
def list_approvals(db: Session = Depends(get_db), _: Principal = Depends(require("read"))) -> list[Approval]:
    return list(db.scalars(select(Approval).order_by(desc(Approval.requested_at))).all())


@router.post("/approvals/{approval_id}/decision")
def decide(approval_id: str, payload: ApprovalDecision, background: BackgroundTasks, db: Session = Depends(get_db), principal: Principal = Depends(require("approval:decide"))) -> dict:
    approval = db.get(Approval, approval_id)
    if not approval: raise HTTPException(404, "Approval not found")
    try:
        run = orchestrator.decide_approval(db, approval, payload.decision, principal.name, payload.comment)
    except OrchestrationError as exc:
        raise HTTPException(409, str(exc)) from exc
    if payload.decision == "approved": background.add_task(orchestrator.resume, run.id)
    return {"run_id": run.id, "status": run.status}


@router.get("/memory")
def list_memory(scope: str | None = None, db: Session = Depends(get_db), _: Principal = Depends(require("read"))) -> list[dict]:
    query = select(Memory).order_by(desc(Memory.created_at))
    if scope: query = query.where(Memory.scope == scope)
    return [{"id": m.id, "scope": m.scope, "owner_id": m.owner_id, "run_id": m.run_id, "content": m.content, "metadata": m.metadata_, "importance": m.importance, "created_at": m.created_at} for m in db.scalars(query.limit(100)).all()]


@router.post("/memory", status_code=201)
def create_memory(payload: MemoryCreate, db: Session = Depends(get_db), principal: Principal = Depends(require("*"))) -> dict:
    memory = Memory(scope=payload.scope, owner_id=payload.owner_id, run_id=payload.run_id, content=payload.content, metadata_=payload.metadata, importance=payload.importance)
    db.add(memory); db.flush(); db.add(AuditLog(actor=principal.name, action="memory.created", resource_type="memory", resource_id=memory.id, details={"scope": memory.scope})); db.commit(); db.refresh(memory)
    return {"id": memory.id, "scope": memory.scope, "content": memory.content}


@router.get("/evaluations", response_model=None)
def list_evaluations(db: Session = Depends(get_db), _: Principal = Depends(require("read"))) -> list[Evaluation]:
    return list(db.scalars(select(Evaluation).order_by(desc(Evaluation.created_at))).all())


@router.post("/evaluations/benchmark", response_model=None)
def benchmark(payload: BenchmarkRequest, db: Session = Depends(get_db), _: Principal = Depends(require("run:create"))) -> list[Evaluation]:
    return BenchmarkRunner().run(db, payload.samples)


@router.get("/analytics")
def analytics(db: Session = Depends(get_db), _: Principal = Depends(require("read"))) -> dict:
    runs = db.scalars(select(Run)).all()
    steps = db.scalars(select(StepRun)).all()
    return {
        "runs_by_status": {status: sum(r.status == status for r in runs) for status in sorted(set(r.status for r in runs))},
        "total_tokens": sum(r.tokens_used for r in runs),
        "estimated_cost_usd": round(sum(r.estimated_cost_usd for r in runs), 6),
        "average_step_latency_ms": round(sum(((s.finished_at - s.started_at).total_seconds() * 1000) for s in steps if s.finished_at and s.started_at) / max(sum(bool(s.finished_at and s.started_at) for s in steps), 1), 2),
        "tool_calls": sum(len(s.tool_calls) for s in steps),
    }


@router.get("/audit", response_model=None)
def audit(db: Session = Depends(get_db), _: Principal = Depends(require("read"))) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(200)).all())
