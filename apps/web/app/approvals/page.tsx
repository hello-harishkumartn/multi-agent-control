import { api } from "@/lib/api";
import { ApprovalActions } from "@/components/ApprovalActions";
import { Status } from "@/components/Status";
export const dynamic="force-dynamic";
type Approval={id:string;run_id:string;reason:string;status:string;decided_by?:string;requested_at:string};
export default async function Page(){const rows=await api<Approval[]>("/approvals",[]);return <><header className="pageHead"><div><p className="eyebrow">GOVERNANCE</p><h1>Approvals</h1><p>Human gates for consequential or high-risk actions.</p></div></header><section className="panel tablePanel"><table><thead><tr><th>Run</th><th>Reason</th><th>Status</th><th>Owner</th><th>Decision</th></tr></thead><tbody>{rows.map(a=><tr key={a.id}><td>{a.run_id.slice(0,8)}</td><td>{a.reason}</td><td><Status value={a.status}/></td><td>{a.decided_by||"Unassigned"}</td><td><ApprovalActions id={a.id} status={a.status}/></td></tr>)}{!rows.length&&<tr><td className="empty" colSpan={5}>No approval requests.</td></tr>}</tbody></table></section></>}

