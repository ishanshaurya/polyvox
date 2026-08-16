from __future__ import annotations

from pathlib import Path


def ensure_project_workspace(data_root: str, project_id: str) -> Path:
    """Create ephemeral per-engagement folders (audio deleted after retention)."""
    root = Path(data_root).resolve()
    project_root = root / "projects" / project_id
    for name in ("recordings", "outputs", "inbox"):
        (project_root / name).mkdir(parents=True, exist_ok=True)
    (project_root / "README.txt").write_text(
        "White-glove engagement workspace.\n"
        "Place customer CDR in inbox/ and recordings under recordings/.\n"
        "Delete this folder when retention_days elapses (see docs/HOSTING.md).\n",
        encoding="utf-8",
    )
    return project_root
