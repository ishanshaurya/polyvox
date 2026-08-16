"""Rubric pack registry — load vertical packs from templates/."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from callqa.config.loader import repo_root


def templates_dir() -> Path:
    return repo_root() / "templates"


def list_rubric_packs() -> list[str]:
    root = templates_dir()
    if not root.is_dir():
        return []
    return sorted(p.stem for p in root.glob("*.yaml"))


def load_rubric_pack(name: str) -> dict[str, Any]:
    path = templates_dir() / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"rubric pack not found: {name}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("analysis_template", name)
    return data


def apply_rubric_pack(cfg: dict, name: str) -> dict:
    """Merge pack under cfg (cfg wins on conflicts)."""
    pack = load_rubric_pack(name)
    merged = dict(pack)
    merged.update(cfg)
    merged["analysis_template"] = name
    return merged
