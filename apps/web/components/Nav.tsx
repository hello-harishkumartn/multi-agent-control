import Link from "next/link";

const items = [
  ["/", "Dashboard"], ["/agents", "Agents"], ["/tools", "Tools"], ["/workflows", "Workflows"],
  ["/runs", "Runs"], ["/memory", "Memory"], ["/evaluations", "Evaluations"],
  ["/approvals", "Approvals"], ["/analytics", "Analytics"],
];

export function Nav() {
  return <aside className="sidebar">
    <div className="brand"><span className="brandMark">A</span><div>AgentPlane<small>CONTROL PLANE</small></div></div>
    <nav>{items.map(([href, label]) => <Link href={href} key={href}>{label}</Link>)}</nav>
    <div className="system"><span className="pulse"/> Local system healthy<br/><small>Postgres · pgvector</small></div>
  </aside>;
}

