"""Analysis profile / rubric pack selection."""

from __future__ import annotations

from callqa.analysis.plugins import generic
from callqa.analysis.rubrics import apply_rubric_pack, list_rubric_packs, load_rubric_pack


def get_profile(cfg: dict):
    """Prompt builder module. Packs share the generic builder; copy comes from cfg."""
    return generic


__all__ = [
    "get_profile",
    "list_rubric_packs",
    "load_rubric_pack",
    "apply_rubric_pack",
]
