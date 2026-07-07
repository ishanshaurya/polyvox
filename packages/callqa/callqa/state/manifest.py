"""Pilot manifest — batch tracking, status, and ASR gate results."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

VALID_STATUSES = frozenset({"downloaded", "transcribed", "analyzed", "reported"})


def manifest_path(cfg: dict) -> str:
    return os.path.join(cfg["output_folder"], "manifests", "pilot_manifest.json")


def load(cfg: dict) -> dict:
    path = manifest_path(cfg)
    if not os.path.exists(path):
        return {"calls": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(cfg: dict, data: dict) -> None:
    path = manifest_path(cfg)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def find_call(data: dict, stem: str) -> dict | None:
    for call in data.get("calls", []):
        if call.get("stem") == stem:
            return call
    return None


def calls_for_batch(data: dict, batch: int | None = None) -> list[dict]:
    calls = data.get("calls", [])
    if batch is None:
        return calls
    return [c for c in calls if c.get("batch") == batch]


def update_call(data: dict, stem: str, **fields: Any) -> dict:
    call = find_call(data, stem)
    if call is None:
        raise KeyError(f"stem not in manifest: {stem}")
    call.update(fields)
    return call


def stems_for_batch(data: dict, batch: int) -> list[str]:
    return [c["stem"] for c in calls_for_batch(data, batch) if c.get("stem")]


def asr_pass_stems(data: dict, batch: int | None = None) -> list[str]:
    """Stems where ASR quality gate passed (or not yet gated but transcribed)."""
    out = []
    for call in calls_for_batch(data, batch):
        if call.get("asr_pass") is True:
            out.append(call["stem"])
    return out


def pending_transcription(data: dict, batch: int) -> list[dict]:
    return [
        c for c in calls_for_batch(data, batch)
        if c.get("status") == "downloaded"
    ]


def pending_analysis(data: dict, batch: int, *, ignore_asr_gate: bool = False) -> list[dict]:
    """Transcribed calls eligible for Claude (asr_pass=true, or all if ignore_asr_gate)."""
    out = []
    for c in calls_for_batch(data, batch):
        if c.get("status") != "transcribed":
            continue
        if ignore_asr_gate or c.get("asr_pass") is True:
            out.append(c)
    return out


def pending_asr_stubs(data: dict, batch: int) -> list[dict]:
    """Transcribed calls that failed ASR — get metadata-only analysis, no Claude."""
    return [
        c for c in calls_for_batch(data, batch)
        if c.get("status") == "transcribed" and c.get("asr_pass") is False
    ]


def agent_slug(name: str) -> str:
    """Agent Name → filesystem-safe slug."""
    return "_".join(name.split())
