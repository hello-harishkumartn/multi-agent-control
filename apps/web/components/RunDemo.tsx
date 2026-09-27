"use client";
import { useState } from "react";

export function RunDemo() {
  const [state, setState] = useState("Run demo");
  async function run() {
    setState("Starting…");
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/runs`, {method: "POST", headers: {"content-type": "application/json", "x-api-key": "local-dev-key"}, body: JSON.stringify({workflow_slug: "saas-churn-response", goal: "Analyze a fictional SaaS company's customer churn problem and produce an action plan."})});
      if (!response.ok) throw new Error();
      const run = await response.json();
      setState("Started");
      window.location.href = `/runs/${run.id}`;
    } catch { setState("API unavailable"); }
  }
  return <button className="primary" onClick={run}>{state} <span>→</span></button>;
}

