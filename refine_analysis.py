"""
Refinement pass: re-transcribe → re-analyze → regenerate Excel for unclear stems.

Usage:
  python refine_analysis.py --unclear
  python refine_analysis.py --agents "Mohammed Mustaque,Akula Varsha"
  python refine_analysis.py --stems-file stems.txt
  python refine_analysis.py --unclear --escalate-model
"""

from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import _bootstrap  # noqa: F401

from callqa.state import manifest
from pipeline_config import load_config


def _parse_stems_file(path: str) -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def _unclear_stems(cfg: dict) -> list[str]:
    analysis_dir = Path(cfg["output_folder"]) / "analysis"
    out: list[str] = []
    for path in sorted(analysis_dir.glob("*.json")):
        if path.name.endswith("_error.txt"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        stem = path.stem
        if data.get("unclear_recording") or data.get("overall_score") in (None, ""):
            out.append(stem)
    return out


def _stems_for_agents(cfg: dict, agents: list[str]) -> list[str]:
    mdata = manifest.load(cfg)
    agent_set = set(agents)
    return [
        c["stem"] for c in mdata.get("calls", [])
        if c.get("agent_name") in agent_set and c.get("stem")
    ]


def _batch_for_stem(mdata: dict, stem: str) -> int | None:
    call = manifest.find_call(mdata, stem)
    return call.get("batch") if call else None


def refine(
    cfg: dict,
    stems: list[str],
    *,
    escalate_model: bool = False,
    skip_report: bool = False,
) -> int:
    if not stems:
        print("\n  No stems to refine.\n")
        return 0

    mdata = manifest.load(cfg)
    by_batch: dict[int, list[str]] = defaultdict(list)
    missing = []
    for stem in stems:
        batch = _batch_for_stem(mdata, stem)
        if batch is None:
            missing.append(stem)
            continue
        by_batch[batch].append(stem)

    if missing:
        print(f"  WARNING: {len(missing)} stem(s) not in manifest: {', '.join(missing[:5])}")

    cascade_flag = ["--cascade-from", "faster-whisper"] if escalate_model else []
    num_batches = int(cfg.get("fetch_limit", 0)) // int(cfg.get("batch_size", 1))

    for batch, batch_stems in sorted(by_batch.items()):
        stem_args: list[str] = []
        for s in batch_stems:
            stem_args.extend(["--stem", s])
        print(f"\n  Refine batch {batch}: {len(batch_stems)} stem(s)")
        subprocess.run(
            [sys.executable, "1_transcribe.py", "--batch", str(batch), "--force", *cascade_flag, *stem_args],
            check=True,
        )
        subprocess.run(
            [sys.executable, "2_analyze.py", "--batch", str(batch), "--force", *stem_args],
            check=True,
        )

    if not skip_report:
        subprocess.run(
            [sys.executable, "3_report.py", "--batch", str(num_batches)],
            check=True,
        )
    return len(stems) - len(missing)


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-transcribe and re-analyze unclear calls")
    parser.add_argument("--unclear", action="store_true", help="All stems with unclear or unscored analysis")
    parser.add_argument("--agents", default="", help="Comma-separated agent names")
    parser.add_argument("--stems-file", default="", help="File with one stem per line")
    parser.add_argument(
        "--escalate-model",
        action="store_true",
        help="Re-transcribe using cascade from faster-whisper only (skip AssemblyAI/Groq)",
    )
    parser.add_argument("--skip-report", action="store_true", help="Skip final 3_report.py")
    args = parser.parse_args()

    cfg = load_config()
    stems: list[str] = []

    if args.unclear:
        stems.extend(_unclear_stems(cfg))
    if args.agents.strip():
        stems.extend(_stems_for_agents(cfg, [a.strip() for a in args.agents.split(",") if a.strip()]))
    if args.stems_file:
        stems.extend(_parse_stems_file(args.stems_file))

    stems = sorted(set(stems))
    n = refine(cfg, stems, escalate_model=args.escalate_model, skip_report=args.skip_report)
    print(f"\n  Refined {n} stem(s).\n")


if __name__ == "__main__":
    main()
