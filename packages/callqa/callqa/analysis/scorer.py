"""QA scoring helpers — stars, weighted overall, JSON extraction, ASR stubs."""

from __future__ import annotations

import json
import re
from datetime import datetime


def score_to_stars(score: float, cfg: dict) -> int:
    bands = cfg["rating_bands"]
    if score >= bands[5]:
        return 5
    if score >= bands[4]:
        return 4
    if score >= bands[3]:
        return 3
    if score >= bands[2]:
        return 2
    return 1


def weighted_overall(kpi_scores: dict, cfg: dict) -> float | None:
    total_w = 0
    acc = 0.0
    for k in cfg["kpis"]:
        val = kpi_scores.get(k["name"])
        if val in (None, ""):
            continue
        try:
            acc += float(val) * k["weight"]
            total_w += k["weight"]
        except (TypeError, ValueError):
            pass
    return round(acc / total_w, 1) if total_w else None


def extract_json(raw_text: str) -> dict:
    txt = raw_text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", txt, re.DOTALL)
    if fence:
        return json.loads(fence.group(1))
    match = re.search(r"\{.*\}", txt, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return json.loads(txt)


def build_asr_fail_stub(meta: dict, cfg: dict, stem: str) -> dict:
    """Metadata-only analysis when ASR gate failed — no Claude call."""
    reasons = meta.get("asr_reasons") or []
    reason_txt = ", ".join(reasons) if reasons else "quality gate failed"
    disp = meta.get("disposition", "")
    outcome = meta.get("call_outcome", "")
    disp_short = disp.split("__")[-1].replace("_", " ") if disp else ""
    qa = (
        f"ASR gate failed ({reason_txt}). KPIs not scored. "
        f"CSV outcome: {outcome}"
        + (f" ({disp_short})" if disp_short else "")
        + ". Action: re-transcribe or manual review."
    )
    return {
        "filename": meta.get("filename", f"{stem}.mp3"),
        "agent_name": meta.get("agent_name", ""),
        "hospital": meta.get("hospital", ""),
        "call_date": meta.get("call_date", ""),
        "csv_disposition": disp,
        "csv_call_outcome": outcome,
        "call_outcome": outcome,
        "call_summary": "",
        "patient_issue": "",
        "kpi_scores": {k["name"]: None for k in cfg["kpis"]},
        "overall_score": None,
        "star_rating": None,
        "escalation_required": False,
        "escalation_severity": "None",
        "escalation_reason": "",
        "patient_complaints": [],
        "positive_observations": [],
        "improvement_areas": [],
        "training_recommended": [],
        "qa_notes": qa,
        "unclear_recording": True,
        "inferred_outcome": "",
        "analyzed_at": datetime.now().isoformat(),
        "_stub": True,
        "_tokens": {"input": 0, "output": 0},
    }
