import { api } from "@/lib/api";
export const dynamic="force-dynamic";
export default async function Page(){const d=await api<Record<string,unknown>>("/analytics",{});return <><header className="pageHead"><div><p className="eyebrow">OBSERVABILITY</p><h1>Analytics</h1><p>Aggregate latency, usage, spend, tool activity, and run health.</p></div></header><section className="kpis">{Object.entries(d).map(([k,v])=><article key={k}><span>{k.replaceAll("_"," ")}</span><strong>{typeof v==="object"?Object.values(v as object).reduce((a:number,b)=>a+Number(b),0):String(v)}</strong><small>{typeof v==="object"?JSON.stringify(v):"Measured across persisted runs"}</small></article>)}</section></>}

