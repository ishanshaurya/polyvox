export type Project = {
  id: string;
  name: string;
  customer_label: string;
  retention_days: number;
  status: string;
  workspace_path: string;
  rubric_pack: string;
  created_at: string;
  notes: string;
  purge_after?: string | null;
};

export type CallRow = {
  id: string;
  stem: string;
  agent_name: string;
  status: string;
  asr_pass: boolean | null;
  overall_score: number | null;
  analysis?: Record<string, unknown> | null;
};

export type JobRow = {
  id: string;
  step: string;
  status: string;
  error: string;
  retries: number;
  created_at: string;
};

const API_BASE = "";

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `request failed: ${res.status}`);
  }
  return res.json();
}

export async function listProjects(): Promise<Project[]> {
  return jsonOrThrow(await fetch(`${API_BASE}/v1/projects`));
}

export async function createProject(input: {
  name: string;
  customer_label: string;
  retention_days?: number;
  rubric_pack?: string;
  notes?: string;
}): Promise<Project> {
  return jsonOrThrow(
    await fetch(`${API_BASE}/v1/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  );
}

export async function getProject(id: string): Promise<Project> {
  return jsonOrThrow(await fetch(`${API_BASE}/v1/projects/${id}`));
}

export async function listCalls(projectId: string): Promise<CallRow[]> {
  return jsonOrThrow(await fetch(`${API_BASE}/v1/projects/${projectId}/calls`));
}

export async function listJobs(projectId: string): Promise<JobRow[]> {
  return jsonOrThrow(await fetch(`${API_BASE}/v1/projects/${projectId}/jobs`));
}

export async function runProject(projectId: string, step = "all"): Promise<JobRow> {
  return jsonOrThrow(
    await fetch(`${API_BASE}/v1/projects/${projectId}/run?step=${encodeURIComponent(step)}`, {
      method: "POST",
    }),
  );
}

export async function uploadCdr(projectId: string, file: File): Promise<{ ok: boolean }> {
  const body = new FormData();
  body.append("file", file);
  return jsonOrThrow(await fetch(`${API_BASE}/v1/projects/${projectId}/cdr`, { method: "POST", body }));
}

export async function uploadRecordings(projectId: string, file: File): Promise<{ ok: boolean; saved: number }> {
  const body = new FormData();
  body.append("file", file);
  return jsonOrThrow(
    await fetch(`${API_BASE}/v1/projects/${projectId}/recordings`, { method: "POST", body }),
  );
}

export async function listRubrics(): Promise<string[]> {
  const data = await jsonOrThrow<{ packs: string[] }>(await fetch(`${API_BASE}/v1/rubrics`));
  return data.packs;
}

export async function getHealth(): Promise<{ ok: boolean }> {
  return jsonOrThrow(await fetch(`${API_BASE}/health`));
}
