import { FormEvent, useEffect, useState } from "react";
import {
  createProject,
  getHealth,
  getProject,
  listCalls,
  listJobs,
  listProjects,
  listRubrics,
  runProject,
  uploadCdr,
  uploadRecordings,
  type CallRow,
  type JobRow,
  type Project,
} from "./api";

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [rubrics, setRubrics] = useState<string[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Project | null>(null);
  const [calls, setCalls] = useState<CallRow[]>([]);
  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [customer, setCustomer] = useState("");
  const [notes, setNotes] = useState("");
  const [rubric, setRubric] = useState("generic");
  const [detailCall, setDetailCall] = useState<CallRow | null>(null);

  async function refreshList() {
    const [health, items, packs] = await Promise.all([getHealth(), listProjects(), listRubrics()]);
    setApiOk(health.ok);
    setProjects(items);
    setRubrics(packs);
    if (packs.length && !packs.includes(rubric)) setRubric(packs[0]);
  }

  async function refreshSelected(id: string) {
    const [proj, callRows, jobRows] = await Promise.all([getProject(id), listCalls(id), listJobs(id)]);
    setSelected(proj);
    setCalls(callRows);
    setJobs(jobRows);
  }

  useEffect(() => {
    void refreshList().catch((err) => {
      setApiOk(false);
      setError(err instanceof Error ? err.message : "API unreachable");
    });
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      setCalls([]);
      setJobs([]);
      return;
    }
    void refreshSelected(selectedId).catch((err) =>
      setError(err instanceof Error ? err.message : "Failed to load project"),
    );
  }, [selectedId]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !customer.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const created = await createProject({
        name: name.trim(),
        customer_label: customer.trim(),
        notes: notes.trim(),
        retention_days: 14,
        rubric_pack: rubric,
      });
      setName("");
      setCustomer("");
      setNotes("");
      await refreshList();
      setSelectedId(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  async function onRun() {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    try {
      await runProject(selectedId, "all");
      await refreshSelected(selectedId);
      await refreshList();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
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
            White-glove QA workspaces. Upload CDR + recordings, run pipeline, read scores on the web.
            Designs land in <code>design/</code>.
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
          <label>
            Rubric pack
            <select value={rubric} onChange={(e) => setRubric(e.target.value)}>
              {(rubrics.length ? rubrics : ["generic", "healthcare"]).map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
          <label className="wide">
            Notes
            <input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="NDA signed · delete after delivery"
            />
          </label>
          <button type="submit" disabled={busy}>
            {busy ? "Working…" : "Create project"}
          </button>
        </form>
        {error ? <p className="error">{error}</p> : null}
      </section>

      <section className="panel">
        <div className="row">
          <h2>Projects</h2>
          <button type="button" className="ghost" onClick={() => void refreshList()}>
            Refresh
          </button>
        </div>
        {projects.length === 0 ? (
          <p className="empty">No projects yet.</p>
        ) : (
          <ul className="list">
            {projects.map((p) => (
              <li key={p.id}>
                <button type="button" className="linkish" onClick={() => setSelectedId(p.id)}>
                  <strong>{p.name}</strong>
                  <span className="muted"> · {p.customer_label}</span>
                </button>
                <div className="meta">
                  <span className="status">{p.status}</span>
                  <span>{p.rubric_pack}</span>
                  <span>{p.retention_days}d</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {selected ? (
        <section className="panel">
          <div className="row">
            <h2>
              {selected.name} <span className="muted">· {selected.customer_label}</span>
            </h2>
            <button type="button" className="ghost" onClick={() => setSelectedId(null)}>
              Close
            </button>
          </div>
          <p className="empty">
            Status <strong>{selected.status}</strong> · pack <code>{selected.rubric_pack}</code> · purge{" "}
            {selected.purge_after || "n/a"}
          </p>
          <div className="actions">
            <label className="file">
              Upload CDR
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (!f || !selectedId) return;
                  void uploadCdr(selectedId, f)
                    .then(() => refreshSelected(selectedId))
                    .catch((err) => setError(err instanceof Error ? err.message : "CDR upload failed"));
                }}
              />
            </label>
            <label className="file">
              Upload MP3 / ZIP
              <input
                type="file"
                accept=".mp3,.zip"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (!f || !selectedId) return;
                  void uploadRecordings(selectedId, f)
                    .then(() => refreshSelected(selectedId))
                    .catch((err) => setError(err instanceof Error ? err.message : "Recording upload failed"));
                }}
              />
            </label>
            <button type="button" disabled={busy} onClick={() => void onRun()}>
              Run pipeline
            </button>
            <a className="ghost buttonish" href={`/v1/projects/${selected.id}/export.xlsx`}>
              Export Excel
            </a>
          </div>

          <h3>Jobs</h3>
          {jobs.length === 0 ? (
            <p className="empty">No jobs yet.</p>
          ) : (
            <ul className="list compact">
              {jobs.map((j) => (
                <li key={j.id}>
                  <span>
                    {j.step} · <strong>{j.status}</strong>
                  </span>
                  {j.error ? <span className="error">{j.error.slice(0, 120)}</span> : null}
                </li>
              ))}
            </ul>
          )}

          <h3>Calls</h3>
          {calls.length === 0 ? (
            <p className="empty">No scored calls yet. Upload recordings and run the pipeline.</p>
          ) : (
            <ul className="list">
              {calls.map((c) => (
                <li key={c.id}>
                  <button type="button" className="linkish" onClick={() => setDetailCall(c)}>
                    <strong>{c.stem}</strong>
                    <span className="muted"> · {c.agent_name || "—"}</span>
                  </button>
                  <div className="meta">
                    <span className="status">{c.status}</span>
                    <span>{c.overall_score == null ? "not scored" : `${c.overall_score}/100`}</span>
                    <span>{c.asr_pass === false ? "ASR fail" : c.asr_pass ? "ASR ok" : ""}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {detailCall ? (
        <section className="panel">
          <div className="row">
            <h2>Call detail</h2>
            <button type="button" className="ghost" onClick={() => setDetailCall(null)}>
              Close
            </button>
          </div>
          <pre className="json">{JSON.stringify(detailCall.analysis || detailCall, null, 2)}</pre>
        </section>
      ) : null}
    </div>
  );
}
