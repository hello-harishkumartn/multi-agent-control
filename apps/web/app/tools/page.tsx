import { ResourcePage } from "@/components/ResourcePage";
export const dynamic = "force-dynamic";
export default function Page(){return <ResourcePage title="Tools" subtitle="Schema-governed capabilities with permissions, risk labels, and timeouts." endpoint="/tools" columns={[["name","Tool"],["description","Description"],["permission","Permission"],["risk_level","Risk"],["timeout_seconds","Timeout (s)"],["mcp_compatible","MCP"]]}/>}

