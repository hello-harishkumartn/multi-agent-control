import { ResourcePage } from "@/components/ResourcePage";
export const dynamic = "force-dynamic";
export default function Page(){return <ResourcePage title="Evaluations" subtitle="Measured single-agent and multi-agent benchmark results; no architecture gets a free pass." endpoint="/evaluations" columns={[["benchmark","Benchmark"],["architecture","Architecture"],["metrics","Measured metrics"],["created_at","Run at"]]}/>}

