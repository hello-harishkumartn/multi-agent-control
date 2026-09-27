type Node = {id: string; agent?: string; kind: string; depends_on?: string[]};

export function WorkflowGraph({nodes}: {nodes: Node[]}) {
  const position: Record<string, [number, number]> = {
    plan: [30, 90], research: [170, 45], analyze: [170, 135], execute: [330, 90], review: [470, 90], verify: [610, 90], approve: [750, 90]
  };
  return <div className="graph"><svg viewBox="0 0 880 190" role="img" aria-label="Workflow graph">
    <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#54647a"/></marker></defs>
    {nodes.flatMap(node => (node.depends_on || []).map(dep => {const a=position[dep]||[0,0], b=position[node.id]||[0,0]; return <path key={`${dep}-${node.id}`} d={`M${a[0]+92},${a[1]+20} C${a[0]+120},${a[1]+20} ${b[0]-24},${b[1]+20} ${b[0]-4},${b[1]+20}`} className="edge" markerEnd="url(#arrow)"/>}))}
    {nodes.map(node => {const [x,y]=position[node.id]||[20,20]; return <g key={node.id} transform={`translate(${x},${y})`}><rect width="94" height="40" rx="8" className={node.kind === "approval" ? "node approval" : "node"}/><circle cx="13" cy="13" r="3" className="nodeDot"/><text x="47" y="18" textAnchor="middle">{node.agent || "Human"}</text><text x="47" y="31" textAnchor="middle" className="nodeType">{node.kind}</text></g>})}
  </svg></div>;
}

