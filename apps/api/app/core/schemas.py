from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AgentCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z][a-z0-9_-]+$")
    name: str
    identity: str
    role: str
    instructions: str
    model: dict[str, Any] = Field(default_factory=lambda: {"provider": "deterministic", "name": "demo-v1"})
    tools: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    memory_config: dict[str, Any] = Field(default_factory=dict)
    context_policy: dict[str, Any] = Field(default_factory=dict)
    budget: dict[str, Any] = Field(default_factory=lambda: {"max_tokens": 4000, "max_cost_usd": 0.25})
    evaluation_policy: dict[str, Any] = Field(default_factory=dict)


class AgentOut(AgentCreate, ORMModel):
    id: str
    enabled: bool


class WorkflowCreate(BaseModel):
    slug: str
    name: str
    description: str
    graph: dict[str, Any]


class WorkflowOut(WorkflowCreate, ORMModel):
    id: str
    version: int
    enabled: bool


class RunCreate(BaseModel):
    workflow_id: str | None = None
    workflow_slug: str | None = "saas-churn-response"
    goal: str = "Analyze a fictional SaaS company's customer churn problem and produce an action plan."
    budget: dict[str, Any] = Field(default_factory=lambda: {"max_cost_usd": 1.0, "max_tokens": 30000})


class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    comment: str = ""


class MemoryCreate(BaseModel):
    scope: Literal["working", "task", "episodic", "semantic"]
    owner_id: str | None = None
    run_id: str | None = None
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    importance: float = Field(default=0.5, ge=0, le=1)


class ToolInvoke(BaseModel):
    arguments: dict[str, Any]


class BenchmarkRequest(BaseModel):
    samples: int = Field(default=3, ge=1, le=20)

