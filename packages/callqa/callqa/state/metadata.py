"""Call metadata resolution — sidecar-first, KIMS filename fallback."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path


def sidecar_path(cfg: dict, stem: str) -> str:
    return os.path.join(cfg["output_folder"], "metadata", f"{stem}.json")


def load_sidecar(cfg: dict, stem: str) -> dict | None:
    path = sidecar_path(cfg, stem)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_sidecar(cfg: dict, stem: str, meta: dict) -> str:
    path = sidecar_path(cfg, stem)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return path


def parse_kims_filename(stem: str) -> dict | None:
    """Legacy KIMS filename format (royalbhrn in stem)."""
    if "royalbhrn" not in stem.lower():
        return None
    parts = stem.split("_")
    result = {
        "agent_name": "Unknown",
        "hospital": "",
        "direction": "",
        "phone": "",
        "call_date": "",
        "call_time": "",
    }
    try:
        idx = next(i for i, p in enumerate(parts) if p.lower() == "royalbhrn")
        name_parts = parts[:idx]
        result["agent_name"] = " ".join(p.capitalize() for p in name_parts if p)
    except StopIteration:
        pass
    parts_upper = [p.upper() for p in parts]
    if "KIMS" in parts_upper:
        result["hospital"] = "KIMS"
    elif "RBH" in parts_upper:
        result["hospital"] = "RBH"
    for p in parts:
        if p.lower() in ("inbound", "outbound"):
            result["direction"] = p.capitalize()
            break
    date_pat = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    time_pat = re.compile(r"^\d{2}-\d{2}-\d{2}$")
    for i, p in enumerate(parts):
        if date_pat.match(p):
            result["call_date"] = p
            if i + 1 < len(parts) and time_pat.match(parts[i + 1]):
                result["call_time"] = parts[i + 1]
            break
    return result


def resolve(cfg: dict, stem: str, audio_path: str | None = None) -> dict:
    """Sidecar first; fall back to KIMS filename parse or minimal stub."""
    sidecar = load_sidecar(cfg, stem)
    if sidecar:
        return sidecar

    parsed = parse_kims_filename(stem)
    if parsed:
        parsed["filename"] = f"{stem}.mp3"
        if audio_path:
            parsed["audio_path"] = audio_path
        return parsed

    # Rainbow stem: AgentSlug_bucket_date_callId8
    m = re.match(
        r"^(?P<agent>.+)_(?P<bucket>b23|b46|b7p)_(?P<date>\d{4}-\d{2}-\d{2})_(?P<cid>[a-f0-9]+)$",
        stem,
        re.I,
    )
    agent_name = stem.replace("_", " ")
    call_date = ""
    duration_bucket = ""
    if m:
        agent_name = m.group("agent").replace("_", " ")
        call_date = m.group("date")
        duration_bucket = m.group("bucket")

    return {
        "filename": f"{stem}.mp3",
        "audio_path": audio_path or "",
        "agent_name": agent_name,
        "hospital": "Rainbow",
        "call_date": call_date,
        "duration_bucket": duration_bucket,
    }
