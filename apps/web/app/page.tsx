import Link from "next/link";
import { api, Run } from "@/lib/api";
import { RunDemo } from "@/components/RunDemo";
import { Status } from "@/components/Status";

export const dynamic = "force-dynamic";

type Dashboard = {counts: {agents:number; runs:number; pending_approvals:number; workflows:number}; recent_runs: Run[]; metrics: {completion_rate:number; tokens:number; cost_usd:number}};
const empty: Dashboard = {counts:{agents:0,runs:0,pending_approvals:0,workflows:0},recent_runs:[],metrics:{completion_rate:0,tokens:0,cost_usd:0}};

export default async function DashboardPage() {
  const data = await api<Dashboard>("/dashboard", empty);
  return <>
    <header className="pageHead"><div><p className="eyebrow">OPERATIONS / OVERVIEW</p><h1>Agent operations</h1><p>Build, govern, and observe every autonomous execution.</p></div><RunDemo/></header>
    <section className="kpis">
      <article><span>Active agents</span><strong>{data.counts.agents}</strong><small>Configured identities</small></article>
      <article><span>Total runs</span><strong>{data.counts.runs}</strong><small>{Math.round(data.metrics.completion_rate*100)}% completion</small></article>
      <article><span>Pending approvals</span><strong className={data.counts.pending_approvals ? "amber":""}>{data.counts.pending_approvals}</strong><small>Human decisions</small></article>
      <article><span>Estimated spend</span><strong>${data.metrics.cost_usd.toFixed(4)}</strong><small>{data.metrics.tokens.toLocaleString()} tokens</small></article>
    </section>
    <div className="dashboardGrid">
      <section className="panel wide"><div className="panelTitle"><div><p className="eyebrow">LIVE ACTIVITY</p><h2>Recent runs</h2></div><Link href="/runs">View all →</Link></div>
        <table><thead><tr><th>Goal</th><th>Status</th><th>Tokens</th><th>Cost</th><th>Created</th></tr></thead><tbody>
          {data.recent_runs.map(run=><tr key={run.id}><td><Link href={`/runs/${run.id}`} className="runLink">{run.goal}</Link><small>{run.id.slice(0,8)}</small></td><td><Status value={run.status}/></td><td>{run.tokens_used.toLocaleString()}</td><td>${run.estimated_cost_usd.toFixed(4)}</td><td>{new Date(run.created_at).toLocaleTimeString()}</td></tr>)}
          {!data.recent_runs.length&&<tr><td colSpan={5} className="empty">No runs yet. Launch the demo workflow to create a trace.</td></tr>}
        </tbody></table>
      </section>
      <section className="panel"><div className="panelTitle"><div><p className="eyebrow">GOVERNANCE</p><h2>System posture</h2></div></div>
        <ul className="checks"><li><span>✓</span><div><strong>Policy enforcement</strong><small>RBAC and per-agent tool grants</small></div></li><li><span>✓</span><div><strong>Durable execution</strong><small>Every node is checkpointed</small></div></li><li><span>✓</span><div><strong>Context isolation</strong><small>Owner-scoped memory filters</small></div></li><li><span>✓</span><div><strong>Human oversight</strong><small>Approval before final release</small></div></li></ul>
      </section>
    </div>
  </>;
}

