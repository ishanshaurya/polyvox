#!/usr/bin/env python3
"""Generate fully-synthetic sample workbooks using the real report builders.

Feeds fake records straight through `packages/callqa/callqa/reports/templates_v1.py`
so `docs/sample_reports/*.xlsx` (and the README screenshots taken from them) match
production format and colors exactly, with zero real patient/agent/hospital data.

Usage:
    python scripts/generate_sample_reports.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "callqa"))

import yaml
from openpyxl import Workbook

from callqa.reports import templates_v1 as T

AGENTS = ["Aria", "Devon", "Priya", "Marcus"]
ISSUES = [
    "Patient wanted to reschedule a follow-up appointment to a later time next week.",
    "Caller asked about insurance coverage for an upcoming procedure.",
    "Patient requested a callback from the billing department about a recent invoice.",
    "Caller wanted to confirm doctor availability for a routine checkup.",
    "Patient asked for prescription refill instructions.",
    "Caller reported difficulty reaching the pharmacy line and wanted a transfer.",
]
OUTCOMES = ["Resolved", "Follow-up Required", "Resolved", "Escalated", "Resolved", "Follow-up Required"]
SCORES = [88, 74, 55, 91, 62, 45]


def make_records(kpi_names: list[str]) -> list[dict]:
    records = []
    for i in range(6):
        overall = SCORES[i]
        kpi_scores = {
            k: max(30, min(95, overall + (5 if j % 2 == 0 else -5)))
            for j, k in enumerate(kpi_names)
        }
        records.append({
            "filename": f"sample_{1000 + i}_call.mp3",
            "agent_name": AGENTS[i % len(AGENTS)],
            "hospital": "Sample General Hospital",
            "call_date": f"2026-0{(i % 6) + 1}-1{i}",
            "patient_issue": ISSUES[i],
            "call_outcome": OUTCOMES[i],
            "overall_score": overall,
            "star_rating": round(overall / 20),
            "kpi_scores": kpi_scores,
            "asr_pass": True,
            "escalation_required": overall < 50,
            "escalation_severity": "High" if overall < 50 else "",
            "escalation_reason": (
                "Agent did not offer an alternative when the request could not be met."
                if overall < 50 else ""
            ),
            "qa_notes": (
                "Call handled within standard script; minor tone inconsistency noted."
                if overall >= 50 else
                "Escalation: patient left without a resolution path; needs supervisor follow-up."
            ),
            "patient_complaints": (
                ["No callback received after the promised timeframe."] if i in (2, 4) else []
            ),
            "_stem": f"sample_{1000 + i}_call",
        })
    return records


def main() -> None:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    kpi_names = [k["name"] for k in cfg["kpis"]]
    records = make_records(kpi_names)

    out_dir = ROOT / "docs" / "sample_reports"
    os.makedirs(out_dir, exist_ok=True)

    builders = [
        ("CALL_LOG_sample", T.build_call_log, {}),
        ("ESCALATIONS_sample", T.build_escalations, {}),
        ("PATIENT_COMPLAINTS_sample", T.build_complaints, {}),
        ("AGENT_EVALUATIONS_sample", T.build_agent_evaluations, {"min_calls": 1}),
    ]
    for name, builder, kwargs in builders:
        wb = Workbook()
        wb.remove(wb.active)
        builder(wb, records, cfg, **kwargs)
        path = out_dir / f"{name}.xlsx"
        wb.save(path)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
