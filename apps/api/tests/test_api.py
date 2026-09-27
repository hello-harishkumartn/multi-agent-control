def test_seeded_control_plane(client):
    agents = client.get("/api/v1/agents").json()
    tools = client.get("/api/v1/tools").json()
    workflows = client.get("/api/v1/workflows").json()
    assert {a["slug"] for a in agents} == {"planner", "researcher", "data-analyst", "executor", "reviewer", "verifier"}
    assert len(tools) == 6
    assert workflows[0]["graph"]["nodes"][-1]["kind"] == "approval"


def test_demo_run_is_durable_and_approval_gated(client):
    response = client.post("/api/v1/runs", json={"workflow_slug": "saas-churn-response", "goal": "Analyze synthetic SaaS churn"})
    assert response.status_code == 202
    run_id = response.json()["id"]
    run = client.get(f"/api/v1/runs/{run_id}").json()
    assert run["status"] == "waiting_approval"
    assert {s["node_id"] for s in run["steps"] if s["status"] == "completed"} >= {"plan", "research", "analyze", "execute", "review", "verify"}
    assert len(run["artifacts"]) == 6
    assert next(s for s in run["steps"] if s["node_id"] == "verify")["output"]["passed"] is True

    approval = client.get("/api/v1/approvals").json()[0]
    result = client.post(f"/api/v1/approvals/{approval['id']}/decision", json={"decision": "approved", "comment": "Evidence reviewed"})
    assert result.status_code == 200
    completed = client.get(f"/api/v1/runs/{run_id}").json()
    assert completed["status"] == "completed"
    assert any(a["name"] == "human-approval" for a in completed["artifacts"])


def test_rbac_blocks_viewer_mutation(client):
    response = client.post("/api/v1/runs", headers={"x-role": "viewer"}, json={"workflow_slug": "saas-churn-response", "goal": "test"})
    assert response.status_code == 403


def test_benchmark_compares_architectures(client):
    response = client.post("/api/v1/evaluations/benchmark", json={"samples": 3})
    assert response.status_code == 200
    results = response.json()
    assert {r["architecture"] for r in results} == {"single-agent", "multi-agent"}
    assert all(r["metrics"]["samples"] == 3 for r in results)

