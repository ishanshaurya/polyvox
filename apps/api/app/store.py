"""In-memory project store for framework scaffold. Replace with Postgres later."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Project:
    id: str
    name: str
    customer_label: str
    retention_days: int
    status: str = "created"  # created | ingested | running | ready | purged
    workspace_path: str = ""
    created_at: str = field(default_factory=_now)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProjectStore:
    def __init__(self) -> None:
        self._items: dict[str, Project] = {}

    def create(
        self,
        *,
        name: str,
        customer_label: str,
        retention_days: int,
        workspace_path: str,
        notes: str = "",
    ) -> Project:
        project = Project(
            id=str(uuid.uuid4()),
            name=name,
            customer_label=customer_label,
            retention_days=retention_days,
            workspace_path=workspace_path,
            notes=notes,
        )
        self._items[project.id] = project
        return project

    def get(self, project_id: str) -> Project | None:
        return self._items.get(project_id)

    def list(self) -> list[Project]:
        return sorted(self._items.values(), key=lambda p: p.created_at, reverse=True)

    def update_status(self, project_id: str, status: str) -> Project | None:
        project = self._items.get(project_id)
        if not project:
            return None
        project.status = status
        return project


store = ProjectStore()
