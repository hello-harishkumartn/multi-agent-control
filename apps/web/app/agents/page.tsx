import { ResourcePage } from "@/components/ResourcePage";
export const dynamic = "force-dynamic";
export default function Page(){return <ResourcePage title="Agents" subtitle="Identity, model, tools, permissions, memory, context, budget, and evaluation policy." endpoint="/agents" columns={[["name","Agent"],["role","Role"],["model","Model"],["tools","Assigned tools"],["budget","Budget"],["enabled","State"]]}/>}

