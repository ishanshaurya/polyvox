"""Load and merge analysis records for reports and dashboards."""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path

from callqa.state import metadata


def load_all_analyses(cfg: dict) -> list[dict]:
    analysis_dir = os.path.join(cfg["output_folder"], "analysis")
    results = []
    for path in sorted(glob.glob(os.path.join(analysis_dir, "*.json"))):
        if path.endswith("_error.txt"):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                data["_json_path"] = path
                results.append(data)
        except Exception as exc:
            print(f"  Could not load {path}: {exc}")
    return results


def merge_records(cfg: dict, analyses: list[dict]) -> list[dict]:
    """Attach CSV-derived fields from metadata sidecars."""
    out = []
    for rec in analyses:
        stem = Path(rec.get("filename", "")).stem or Path(rec.get("_json_path", "")).stem
        if not stem:
            out.append(rec)
            continue
        meta = metadata.load_sidecar(cfg, stem) or {}
        merged = {**rec}
        merged["call_outcome"] = meta.get("call_outcome") or rec.get("call_outcome", "")
        merged["center"] = meta.get("center", "")
        merged["disposition"] = meta.get("disposition", "")
        merged["asr_pass"] = meta.get("asr_pass", not rec.get("unclear_recording"))
        kpi = rec.get("kpi_scores") or {}
        if any(v not in (None, "") for v in kpi.values()):
            merged["asr_pass"] = True
        out.append(merged)
    return out
