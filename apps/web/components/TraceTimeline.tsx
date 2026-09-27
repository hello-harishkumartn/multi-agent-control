import { Step } from "@/lib/api";
import { Status } from "./Status";

export function TraceTimeline({steps}: {steps: Step[]}) {
  const start = Math.min(...steps.filter(s=>s.started_at).map(s=>new Date(s.started_at!).getTime()), Date.now());
  const end = Math.max(...steps.filter(s=>s.finished_at).map(s=>new Date(s.finished_at!).getTime()), start + 1);
  return <div className="trace">
    <div className="traceHeader"><span>Execution trace</span><span>0 ms</span><span>{end-start} ms</span></div>
    {steps.map(step => {
      const s = step.started_at ? new Date(step.started_at).getTime() : start;
      const e = step.finished_at ? new Date(step.finished_at).getTime() : s + 10;
      const left = ((s-start)/(end-start))*78; const width=Math.max(2, ((e-s)/(end-start))*78);
      return <div className="traceRow" key={step.id}><div><strong>{step.node_id}</strong><small>{step.model_info?.name || "control node"}</small></div><div className="track"><span style={{left: `${left}%`, width: `${width}%`}} className={`bar ${step.status}`}/></div><Status value={step.status}/><code>{step.tokens} tok</code></div>
    })}
  </div>;
}

