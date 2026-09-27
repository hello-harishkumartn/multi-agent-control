import { ResourcePage } from "@/components/ResourcePage";
export const dynamic = "force-dynamic";
export default function Page(){return <ResourcePage title="Memory" subtitle="Explicit working, task, episodic, and semantic records—not raw conversation dumps." endpoint="/memory" columns={[["scope","Scope"],["content","Content"],["owner_id","Private owner"],["importance","Importance"],["created_at","Created"]]}/>}

