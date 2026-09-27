from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.models import Agent, Memory, Run, Workflow
from app.services.context import ContextManager


def test_context_isolates_private_memory_and_tracks_manifest():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        workflow = Workflow(slug="w", name="w", description="", graph={"nodes": []})
        owner = Agent(slug="owner", name="owner", identity="", role="", instructions="", model={}, tools=[], permissions=[], memory_config={}, context_policy={}, budget={}, evaluation_policy={})
        other = Agent(slug="other", name="other", identity="", role="", instructions="", model={}, tools=[], permissions=[], memory_config={}, context_policy={}, budget={}, evaluation_policy={})
        db.add_all([workflow, owner, other]); db.flush()
        run = Run(workflow_id=workflow.id, goal="churn", state={}, budget={}); db.add(run); db.flush()
        db.add_all([
            Memory(scope="semantic", owner_id=owner.id, content="private churn fact", importance=1),
            Memory(scope="semantic", owner_id=other.id, content="other secret", importance=1),
            Memory(scope="task", content="shared churn artifact", importance=.8),
        ]); db.commit()
        bundle = ContextManager().build(db, run_id=run.id, agent_id=owner.id, goal="churn", policy={"max_context_tokens": 100, "memory_scopes": ["semantic", "task"]})
        text = str(bundle.items)
        assert "private churn fact" in text and "shared churn artifact" in text
        assert "other secret" not in text
        assert bundle.manifest()["policy"]["isolation"] == "owner-or-shared"

