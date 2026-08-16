export type Project = {
  id: string;
  name: string;
  customer_label: string;
  retention_days: number;
  status: string;
  workspace_path: string;
  created_at: string;
  notes: string;
};

const API_BASE = "";

export async function listProjects(): Promise<Project[]> {
  const res = await fetch(`${API_BASE}/v1/projects`);
  if (!res.ok) throw new Error(`list projects failed: ${res.status}`);
  return res.json();
}

export async function createProject(input: {
  name: string;
  customer_label: string;
  retention_days?: number;
  notes?: string;
}): Promise<Project> {
  const res = await fetch(`${API_BASE}/v1/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `create failed: ${res.status}`);
  }
  return res.json();
}

export async function getHealth(): Promise<{ ok: boolean }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("API unreachable");
  return res.json();
}
