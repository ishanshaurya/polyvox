#!/usr/bin/env python3
"""Worker — runs callqa pipeline steps against a project workspace."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "packages" / "callqa"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PolyVox worker")
    parser.add_argument("--project-workspace", required=True)
    parser.add_argument(
        "--step",
        choices=["fetch", "transcribe", "analyze", "report", "all"],
        default="all",
    )
    parser.add_argument("--rubric-pack", default="generic")
    parser.add_argument("--project-id", default="")
    parser.add_argument("--batch", type=int, default=1)
    args = parser.parse_args(argv)

    workspace = Path(args.project_workspace).resolve()
    if not workspace.is_dir():
        print(f"ERROR: workspace not found: {workspace}", file=sys.stderr)
        return 1

    from callqa.analysis.rubrics import apply_rubric_pack
    from callqa.config.loader import load_config
    from callqa.core.pipeline import run_analyze, run_export, run_transcribe, store_from_workspace
    from callqa.state import manifest

    cfg = load_config()
    cfg = apply_rubric_pack(cfg, args.rubric_pack)
    store = store_from_workspace(workspace)
    pipeline_cfg = store.as_pipeline_cfg(cfg)

    # Seed a minimal manifest from recordings if none exists (ZIP upload path)
    data = manifest.load(pipeline_cfg)
    if not data.get("calls"):
        calls = []
        for i, mp3 in enumerate(sorted((workspace / "recordings").glob("*.mp3"))):
            stem = mp3.stem
            calls.append(
                {
                    "stem": stem,
                    "call_id": stem,
                    "agent_name": "",
                    "duration_bucket": "any",
                    "batch": 1,
                    "status": "downloaded",
                    "asr_pass": None,
                    "asr_metrics": {},
                    "fields_populated": ["agent_name", "call_date", "call_outcome"],
                    "fields_blank": [
                        "patient_issue",
                        "kpi_scores",
                        "complaints",
                        "escalations",
                        "qa_notes",
                    ],
                }
            )
        if calls:
            manifest.save(
                pipeline_cfg,
                {
                    "created_at": "",
                    "csv_path": str(workspace / "inbox"),
                    "calls": calls,
                },
            )

    print(f"PolyVox worker  workspace={workspace}  step={args.step}  pack={args.rubric_pack}")

    if args.step in {"transcribe", "all"}:
        n = run_transcribe(pipeline_cfg, store, batch=args.batch)
        print(f"  transcribed: {n}")
    if args.step in {"analyze", "all"}:
        n = run_analyze(pipeline_cfg, store, batch=args.batch)
        print(f"  analyzed: {n}")
    if args.step in {"report", "all"}:
        art = run_export(pipeline_cfg, store, batch=args.batch)
        print(f"  reports: {len(art.paths)}")
    if args.step == "fetch":
        print("  fetch: use API CDR upload + recordings endpoints (URL fetch still via 0_fetch_csv.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
