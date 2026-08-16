import { FormEvent, useEffect, useState } from "react";
import { createProject, getHealth, listProjects, type Project } from "./api";

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [customer, setCustomer] = useState("");
  const [notes, setNotes] = useState("");

  async function refresh() {
    try {
      setError(null);
      const [health, items] = await Promise.all([getHealth(), listProjects()]);
      setApiOk(health.ok);
      setProjects(items);
    } catch (err) {
      setApiOk(false);
      setError(err instanceof Error ? err.message : "Failed to reach API");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !customer.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createProject({
        name: name.trim(),
        customer_label: customer.trim(),
        notes: notes.trim(),
        retention_days: 14,
      });
      setName("");
      setCustomer("");
      setNotes("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <header className="top">
        <div>
          <p className="brand">PolyVox</p>
          <h1>Engagements</h1>
          <p className="lede">
            White-glove QA workspaces. Short retention. Design assets go in{" "}
            <code>design/</code>.
          </p>
        </div>
        <div className={`pill ${apiOk ? "ok" : apiOk === false ? "bad" : ""}`}>
          {apiOk === null ? "Checking API…" : apiOk ? "API online" : "API offline"}
        </div>
      </header>

      <section className="panel">
        <h2>New engagement</h2>
        <form className="form" onSubmit={onSubmit}>
          <label>
            Project name
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="March QA cohort" />
          </label>
          <label>
            Customer
            <input value={customer} onChange={(e) => setCustomer(e.target.value)} placeholder="Acme Support" />
          </label>
          <label className="wide">
            Notes
            <input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="NDA signed · delete after delivery" />
          </label>
          <button type="submit" disabled={busy}>
            {busy ? "Creating…" : "Create project"}
          </button>
        </form>
        {error ? <p className="error">{error}</p> : null}
      </section>

      <section className="panel">
        <div className="row">
          <h2>Projects</h2>
          <button type="button" className="ghost" onClick={() => void refresh()}>
            Refresh
          </button>
        </div>
        {projects.length === 0 ? (
          <p className="empty">No projects yet. Create one to allocate a local workspace.</p>
        ) : (
          <ul className="list">
            {projects.map((p) => (
              <li key={p.id}>
                <div>
                  <strong>{p.name}</strong>
                  <span className="muted"> · {p.customer_label}</span>
                </div>
                <div className="meta">
                  <span className="status">{p.status}</span>
                  <span>{p.retention_days}d retention</span>
                  <code title={p.workspace_path}>{p.id.slice(0, 8)}</code>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
