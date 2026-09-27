import { api } from "@/lib/api";
import { Status } from "./Status";

export async function ResourcePage({title, subtitle, endpoint, columns}: {title: string; subtitle: string; endpoint: string; columns: [string,string][]}) {
  const rows = await api<Record<string, unknown>[]>(endpoint, []);
  return <><header className="pageHead"><div><p className="eyebrow">CONTROL PLANE</p><h1>{title}</h1><p>{subtitle}</p></div></header><section className="panel tablePanel">
    <div className="panelTitle"><h2>{title}</h2><span>{rows.length} records</span></div>
    <div className="tableWrap"><table><thead><tr>{columns.map(([key,label])=><th key={key}>{label}</th>)}</tr></thead><tbody>
      {rows.map((row,i)=><tr key={String(row.id || i)}>{columns.map(([key])=><td key={key}>{key === "status" ? <Status value={String(row[key])}/> : render(row[key])}</td>)}</tr>)}
      {!rows.length && <tr><td colSpan={columns.length} className="empty">No records yet. Start the API to populate this view.</td></tr>}
    </tbody></table></div>
  </section></>;
}

function render(value: unknown) {
  if (typeof value === "boolean") return value ? "Enabled" : "Disabled";
  if (value && typeof value === "object") return <code className="json">{JSON.stringify(value)}</code>;
  return String(value ?? "—");
}

