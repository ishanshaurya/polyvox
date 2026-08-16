"""Project + upload + run + calls API (Phase 1)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.db.models import Call, Job, Project
from app.db.session import init_db, session as db_session
from app.settings import settings
from app.workspace import ensure_project_workspace

router = APIRouter(tags=["projects"])


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    customer_label: str = Field(min_length=1, max_length=200)
    retention_days: int | None = Field(default=None, ge=1, le=90)
    rubric_pack: str | None = None
    notes: str = ""


class ProjectOut(BaseModel):
    id: str
    name: str
    customer_label: str
    retention_days: int
    status: str
    workspace_path: str
    rubric_pack: str
    created_at: str
    notes: str
    purge_after: str | None = None


class CallOut(BaseModel):
    id: str
    stem: str
    agent_name: str
    status: str
    asr_pass: bool | None
    overall_score: float | None = None
    analysis: dict | None = None


class JobOut(BaseModel):
    id: str
    step: str
    status: str
    error: str
    retries: int
    created_at: str


def _project_out(p: Project) -> ProjectOut:
    return ProjectOut(
        id=p.id,
        name=p.name,
        customer_label=p.customer_label,
        retention_days=p.retention_days,
        status=p.status,
        workspace_path=p.workspace_path,
        rubric_pack=p.rubric_pack,
        created_at=p.created_at.isoformat() if p.created_at else "",
        notes=p.notes or "",
        purge_after=p.purge_after.isoformat() if p.purge_after else None,
    )


@router.post("/projects", response_model=ProjectOut)
def create_project(body: ProjectCreate) -> ProjectOut:
    init_db()
    retention = body.retention_days or settings.default_retention_days
    project_id = str(uuid.uuid4())
    workspace = ensure_project_workspace(settings.data_root, project_id)
    now = datetime.now(timezone.utc)
    project = Project(
        id=project_id,
        name=body.name.strip(),
        customer_label=body.customer_label.strip(),
        retention_days=retention,
        status="created",
        workspace_path=str(workspace),
        rubric_pack=(body.rubric_pack or settings.default_rubric_pack).strip(),
        notes=body.notes.strip(),
        created_at=now,
        purge_after=now + timedelta(days=retention),
    )
    with db_session() as s:
        s.add(project)
        s.commit()
        s.refresh(project)
        return _project_out(project)


@router.get("/projects", response_model=list[ProjectOut])
def list_projects() -> list[ProjectOut]:
    init_db()
    with db_session() as s:
        rows = s.query(Project).order_by(Project.created_at.desc()).all()
        return [_project_out(p) for p in rows]


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str) -> ProjectOut:
    init_db()
    with db_session() as s:
        p = s.get(Project, project_id)
        if not p:
            raise HTTPException(status_code=404, detail="project not found")
        return _project_out(p)


@router.post("/projects/{project_id}/cdr")
async def upload_cdr(project_id: str, file: UploadFile = File(...)) -> dict:
    init_db()
    with db_session() as s:
        p = s.get(Project, project_id)
        if not p:
            raise HTTPException(status_code=404, detail="project not found")
        inbox = Path(p.workspace_path) / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        dest = inbox / (file.filename or "calls.csv")
        content = await file.read()
        dest.write_bytes(content)
        p.status = "ingested"
        s.commit()
        return {"ok": True, "path": str(dest), "bytes": len(content)}


@router.post("/projects/{project_id}/recordings")
async def upload_recordings(project_id: str, file: UploadFile = File(...)) -> dict:
    init_db()
    with db_session() as s:
        p = s.get(Project, project_id)
        if not p:
            raise HTTPException(status_code=404, detail="project not found")
        rec_dir = Path(p.workspace_path) / "recordings"
        rec_dir.mkdir(parents=True, exist_ok=True)
        raw = await file.read()
        name = (file.filename or "upload.bin").lower()
        saved = 0
        if name.endswith(".zip"):
            tmp = Path(p.workspace_path) / "inbox" / "recordings.zip"
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_bytes(raw)
            with zipfile.ZipFile(tmp) as zf:
                for info in zf.infolist():
                    if info.is_dir() or not info.filename.lower().endswith(".mp3"):
                        continue
                    target = rec_dir / Path(info.filename).name
                    with zf.open(info) as src, open(target, "wb") as out:
                        shutil.copyfileobj(src, out)
                    saved += 1
        elif name.endswith(".mp3"):
            (rec_dir / Path(file.filename or "recording.mp3").name).write_bytes(raw)
            saved = 1
        else:
            raise HTTPException(status_code=400, detail="upload a .mp3 or .zip of mp3s")
        p.status = "ingested"
        s.commit()
        return {"ok": True, "saved": saved}


@router.post("/projects/{project_id}/run", response_model=JobOut)
def run_pipeline(project_id: str, step: str = "all") -> JobOut:
    init_db()
    allowed = {"transcribe", "analyze", "report", "all"}
    if step not in allowed:
        raise HTTPException(status_code=400, detail=f"step must be one of {sorted(allowed)}")
    with db_session() as s:
        p = s.get(Project, project_id)
        if not p:
            raise HTTPException(status_code=404, detail="project not found")
        job = Job(
            id=str(uuid.uuid4()),
            project_id=project_id,
            step=step,
            status="queued",
        )
        s.add(job)
        p.status = "running"
        s.commit()
        s.refresh(job)

        worker = Path(__file__).resolve().parents[2].parent / "worker" / "main.py"
        cmd = [
            sys.executable,
            str(worker),
            "--project-workspace",
            p.workspace_path,
            "--step",
            step,
            "--rubric-pack",
            p.rubric_pack,
            "--project-id",
            project_id,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            job.status = "done" if result.returncode == 0 else "failed"
            job.error = "" if result.returncode == 0 else (result.stderr or result.stdout)[-2000:]
            job.finished_at = datetime.now(timezone.utc)
            p.status = "ready" if result.returncode == 0 else "failed"
        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = datetime.now(timezone.utc)
            p.status = "failed"
        s.add(job)
        s.commit()
        s.refresh(job)
        return JobOut(
            id=job.id,
            step=job.step,
            status=job.status,
            error=job.error or "",
            retries=job.retries,
            created_at=job.created_at.isoformat() if job.created_at else "",
        )


@router.get("/projects/{project_id}/jobs", response_model=list[JobOut])
def list_jobs(project_id: str) -> list[JobOut]:
    init_db()
    with db_session() as s:
        rows = s.query(Job).filter(Job.project_id == project_id).order_by(Job.created_at.desc()).all()
        return [
            JobOut(
                id=j.id,
                step=j.step,
                status=j.status,
                error=j.error or "",
                retries=j.retries,
                created_at=j.created_at.isoformat() if j.created_at else "",
            )
            for j in rows
        ]


@router.get("/projects/{project_id}/calls", response_model=list[CallOut])
def list_calls(project_id: str) -> list[CallOut]:
    init_db()
    with db_session() as s:
        p = s.get(Project, project_id)
        if not p:
            raise HTTPException(status_code=404, detail="project not found")
        workspace = p.workspace_path
        rows = s.query(Call).filter(Call.project_id == project_id).all()
        if rows:
            out = []
            for c in rows:
                score = None
                if c.analysis_json and c.analysis_json.get("overall_score") not in (None, ""):
                    try:
                        score = float(c.analysis_json["overall_score"])
                    except (TypeError, ValueError):
                        score = None
                out.append(
                    CallOut(
                        id=c.id,
                        stem=c.stem,
                        agent_name=c.agent_name,
                        status=c.status,
                        asr_pass=c.asr_pass,
                        overall_score=score,
                        analysis=c.analysis_json,
                    )
                )
            return out

    analysis_dir = Path(workspace) / "outputs" / "analysis"
    results: list[CallOut] = []
    if analysis_dir.is_dir():
        for path in sorted(analysis_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            score = data.get("overall_score")
            try:
                overall = float(score) if score not in (None, "") else None
            except (TypeError, ValueError):
                overall = None
            results.append(
                CallOut(
                    id=path.stem,
                    stem=path.stem,
                    agent_name=str(data.get("agent_name") or ""),
                    status="analyzed",
                    asr_pass=not bool(data.get("unclear_recording")),
                    overall_score=overall,
                    analysis=data,
                )
            )
    return results


@router.get("/calls/{call_id}", response_model=CallOut)
def get_call(call_id: str) -> CallOut:
    init_db()
    with db_session() as s:
        c = s.get(Call, call_id)
        if c:
            score = None
            if c.analysis_json and c.analysis_json.get("overall_score") not in (None, ""):
                try:
                    score = float(c.analysis_json["overall_score"])
                except (TypeError, ValueError):
                    score = None
            return CallOut(
                id=c.id,
                stem=c.stem,
                agent_name=c.agent_name,
                status=c.status,
                asr_pass=c.asr_pass,
                overall_score=score,
                analysis=c.analysis_json,
            )
    raise HTTPException(
        status_code=404,
        detail="call not found — use /projects/{id}/calls for workspace-scanned analyses",
    )


@router.get("/projects/{project_id}/export.xlsx")
def export_xlsx(project_id: str):
    init_db()
    with db_session() as s:
        p = s.get(Project, project_id)
        if not p:
            raise HTTPException(status_code=404, detail="project not found")
        reports = Path(p.workspace_path) / "outputs" / "reports"
        files = sorted(reports.glob("*.xlsx")) if reports.is_dir() else []
        if not files:
            raise HTTPException(status_code=404, detail="no reports yet — run pipeline first")
        latest = max(files, key=lambda f: f.stat().st_mtime)
        return FileResponse(latest, filename=latest.name)


@router.get("/rubrics")
def list_rubrics() -> dict:
    try:
        pkg = Path(__file__).resolve().parents[4] / "packages" / "callqa"
        if str(pkg) not in sys.path:
            sys.path.insert(0, str(pkg))
        from callqa.analysis.rubrics import list_rubric_packs

        return {"packs": list_rubric_packs()}
    except Exception:  # noqa: BLE001
        root = Path(__file__).resolve().parents[4] / "templates"
        packs = sorted(p.stem for p in root.glob("*.yaml")) if root.is_dir() else []
        return {"packs": packs}


@router.post("/projects/{project_id}/purge-media")
def purge_media(project_id: str) -> dict:
    init_db()
    with db_session() as s:
        p = s.get(Project, project_id)
        if not p:
            raise HTTPException(status_code=404, detail="project not found")
        workspace = Path(p.workspace_path)
        removed = 0
        for rel in ("recordings", "outputs/transcripts"):
            d = workspace / rel
            if d.is_dir():
                for f in d.iterdir():
                    if f.is_file():
                        f.unlink()
                        removed += 1
        p.status = "purged"
        s.commit()
        return {"ok": True, "removed_files": removed}
