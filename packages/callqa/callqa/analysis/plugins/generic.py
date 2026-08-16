"""Configurable call-center QA profile (rubric pack driven)."""

from __future__ import annotations

import json


def build_system_prompt(cfg: dict) -> str:
    kpi_list = "\n".join(
        f"  - {k['name']} (weight {k['weight']}%): {k['description']}"
        for k in cfg["kpis"]
    )
    training_list = "\n".join(f"  - {t}" for t in cfg.get("training_modules", []))
    subject = cfg.get("subject_label") or "customer"
    domain = cfg.get("domain_label") or "call center"

    return f"""You are a senior {domain} Quality Assurance specialist.
Analyze agent-{subject} interactions and return ONLY valid JSON — no preamble, no markdown.

IMPORTANT: The agent_name field is provided from call metadata. Use exactly the name given.

SCORING CRITERIA — Score each KPI 0 to 100:
{kpi_list}

SCORING RULES:
  - Use the full 0–100 range with integer scores.
  - Be discriminating; scores should reflect what actually happened in the call.

ESCALATION RULES — set escalation_required: true only for behavioral issues:
  - Agent rude, dismissive, sarcastic, or condescending
  - {subject.capitalize()} in distress and agent does not acknowledge or help
  - Agent gives clearly incorrect information
  - Unprofessional, threatening, or inappropriate language
  Do NOT escalate solely because CSV disposition disagrees with transcript — note that in qa_notes instead.

DISPOSITION VERIFICATION:
  - csv_call_outcome is provided from operational data (do not change it).
  - Infer what happened in the call from the transcript only.
  - If your inferred outcome clearly conflicts with csv_call_outcome AND the transcript is intelligible,
    add a note in qa_notes: "Disposition mismatch: CSV says <csv_call_outcome> but call suggests <your inference>."

UNCLEAR / SHORT TRANSCRIPTS:
  - If transcript is gibberish or too short to judge: set unclear_recording: true
  - Leave patient_issue, kpi_scores, complaints empty or null — do not invent content.

TRAINING MODULES (recommend 1–3 from this list only):
{training_list}"""


def build_user_prompt(
    transcript: str,
    filename: str,
    agent_name: str,
    cfg: dict,
    *,
    hospital: str = "",
    call_date: str = "",
    csv_call_outcome: str = "",
    csv_disposition: str = "",
    unclear: bool = False,
) -> str:
    kpi_names = [k["name"] for k in cfg["kpis"]]
    kpi_json = {name: "0-100" for name in kpi_names}
    site = hospital or cfg.get("site_name") or ""
    site_line = f"\nSITE: {site}" if site else ""
    date_line = f"\nCALL DATE: {call_date}" if call_date else ""
    disp_line = f"\nCSV DISPOSITION: {csv_disposition}" if csv_disposition else ""
    outcome_line = f"\nCSV CALL OUTCOME (operational): {csv_call_outcome}" if csv_call_outcome else ""
    unclear_note = (
        "\nNOTE: Transcript failed ASR quality gate or is very short. "
        "Set unclear_recording: true; do not score KPIs."
        if unclear else ""
    )
    domain = cfg.get("domain_label") or "call center"

    return f"""Analyze this {domain} transcript:

FILE: {filename}
AGENT: {agent_name}{site_line}{date_line}{disp_line}{outcome_line}{unclear_note}

<transcript>
{transcript}
</transcript>

Return ONLY this JSON:
{{
  "filename": "{filename}",
  "agent_name": "{agent_name}",
  "hospital": "{site}",
  "call_date": "{call_date}",
  "csv_disposition": "{csv_disposition}",
  "csv_call_outcome": "{csv_call_outcome}",
  "call_summary": "3-4 sentence factual summary or empty if unclear",
  "patient_issue": "one sentence or empty if unclear",
  "kpi_scores": {json.dumps(kpi_json, indent=4)},
  "overall_score": "weighted average 0-100 or null if unclear",
  "star_rating": "1-5 or null if unclear",
  "escalation_required": true | false,
  "escalation_severity": "None" | "Low" | "Medium" | "High" | "Critical",
  "escalation_reason": "behavioral reason or empty",
  "patient_complaints": ["complaint strings"],
  "positive_observations": ["specific strengths"],
  "improvement_areas": ["specific improvements"],
  "training_recommended": ["module names from approved list"],
  "qa_notes": "manager notes including disposition mismatch if any",
  "unclear_recording": true | false,
  "inferred_outcome": "your best inference from transcript or empty if unclear"
}}"""
