const API = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function api<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${API}/api/v1${path}`, { cache: "no-store", headers: { "x-api-key": "local-dev-key" } });
    if (!response.ok) return fallback;
    return response.json();
  } catch {
    return fallback;
  }
}

export type Run = {
  id: string; goal: string; status: string; tokens_used: number; estimated_cost_usd: number;
  created_at: string; started_at?: string; finished_at?: string; state?: Record<string, unknown>; steps?: Step[]; artifacts?: {name: string; content: unknown}[];
};
export type Step = { id: string; node_id: string; status: string; attempt: number; model_info: Record<string, string>; context_manifest: {token_estimate?: number; items?: unknown[]}; tool_calls: unknown[]; tokens: number; estimated_cost_usd: number; started_at?: string; finished_at?: string; output: Record<string, unknown>; evaluation: Record<string, unknown>; error?: string };

