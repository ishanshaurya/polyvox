from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.settings import settings
from app.store import store
from app.workspace import ensure_project_workspace

router = APIRouter(tags=["projects"])


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    customer_label: str = Field(min_length=1, max_length=200)
    retention_days: int | None = Field(default=None, ge=1, le=90)
    notes: str = ""


class ProjectOut(BaseModel):
    id: str
    name: str
    customer_label: str
    retention_days: int
    status: str
    workspace_path: str
    created_at: str
    notes: str


@router.post("/projects", response_model=ProjectOut)
def create_project(body: ProjectCreate) -> ProjectOut:
    retention = body.retention_days or settings.default_retention_days
    project = store.create(
        name=body.name.strip(),
        customer_label=body.customer_label.strip(),
        retention_days=retention,
        workspace_path="",
        notes=body.notes.strip(),
    )
    workspace = ensure_project_workspace(settings.data_root, project.id)
    project.workspace_path = str(workspace)
    return ProjectOut(**project.to_dict())


@router.get("/projects", response_model=list[ProjectOut])
def list_projects() -> list[ProjectOut]:
    return [ProjectOut(**p.to_dict()) for p in store.list()]


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str) -> ProjectOut:
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    return ProjectOut(**project.to_dict())


@router.post("/projects/{project_id}/mark/{status}", response_model=ProjectOut)
def mark_status(project_id: str, status: str) -> ProjectOut:
    allowed = {"created", "ingested", "running", "ready", "purged"}
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(allowed)}")
    project = store.update_status(project_id, status)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    return ProjectOut(**project.to_dict())
