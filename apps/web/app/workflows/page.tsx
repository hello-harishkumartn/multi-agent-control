import { api } from "@/lib/api";
import { WorkflowGraph } from "@/components/WorkflowGraph";
export const dynamic = "force-dynamic";
type Workflow={id:string;name:string;description:string;version:number;graph:{nodes:{id:string;agent?:string;kind:string;depends_on?:string[]}[]}};
export default async function Page(){const rows=await api<Workflow[]>("/workflows",[]);return <><header className="pageHead"><div><p className="eyebrow">ORCHESTRATION</p><h1>Workflows</h1><p>Durable DAGs with parallel fan-out, retries, fallback, verification, and approval gates.</p></div></header>{rows.map(w=><section className="panel workflow" key={w.id}><div className="panelTitle"><div><p className="eyebrow">VERSION {w.version}</p><h2>{w.name}</h2><p>{w.description}</p></div><span>{w.graph.nodes.length} nodes</span></div><WorkflowGraph nodes={w.graph.nodes}/></section>)}{!rows.length&&<section className="panel empty">Start the API to load the demo workflow.</section>}</>}

