# PolyVox

**Multilingual call QA, automated** — telephony export → transcription → AI scoring → Excel reports.

*Built for Rainbow Hospitals — automating QA for their multilingual call center.*

---

## The problem

Call centers face three bottlenecks at once:

1. **Manual QA doesn't scale** — managers can only listen to a fraction of calls; scores vary by reviewer.
2. **Multilingual recordings** — English, Hindi, Telugu, and more make consistent human review slow and expensive.
3. **Data without deliverables** — CDR exports pile up, but QA teams need structured Excel reports they can act on the same week.

PolyVox closes that gap: ingest a CSV, run overnight, deliver four workbooks.

---

## What it does

```
telephony CSV  →  fetch MP3s  →  transcribe (ASR cascade)  →  Claude KPI scoring  →  Excel reports
```

| Output | Purpose |
|---|---|
| **CALL_LOG** | Every call scored on 9 KPIs with QA notes |
| **ESCALATIONS** | Behavioral flags (rude/dismissive) — not low scores alone |
| **PATIENT_COMPLAINTS** | Complaints extracted per call |
| **AGENT_EVALUATIONS** | Per-agent rollup + training recommendations |

Designed for **100+ calls per cohort**, batched and **resume-safe** (restart after rate limits without redoing finished work).

### Sample output

![Call log](docs/screenshots/call-log.png)
![Agent evaluations](docs/screenshots/agent-evaluations.png)
![Escalations](docs/screenshots/escalations.png)

*Names, dates, and identifiers redacted for privacy.*

---

## Results

- **Time** — hours of manual listening replaced by an automated batch pipeline
- **Consistency** — the same weighted KPI rubric applied to every call
- **Actionable** — four Excel reports QA can share with team leads immediately

---

## Stack

Python · Groq Whisper / AssemblyAI / faster-whisper · Claude · pandas · openpyxl

Configurable via `config.yaml`: agents, KPI weights, ASR thresholds, language hints, analysis profile.

---

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ANTHROPIC_API_KEY, GROQ_API_KEY

# Add your telephony CSV at data/calls.csv (see data/README.md)
python 0_fetch_csv.py --dry-run
python run_all.py          # small cohorts
./run_pipeline.sh          # large cohorts
```

Details: `PIPELINE_RUNBOOK.md` · unclear recordings: `REFINE_ANALYSIS.md`

---

## Project layout

```
polyvox/
├── 0_fetch_csv.py … 3_report.py
├── packages/callqa/       # ingestion, transcription, analysis, reports
├── config.yaml
└── templates/healthcare.yaml
```
