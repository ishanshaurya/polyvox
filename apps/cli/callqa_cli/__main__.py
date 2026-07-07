"""Call QA CLI — fetch, transcribe, analyze, report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure callqa package is importable when running without pip install
_ROOT = Path(__file__).resolve().parents[3]
_PKG = _ROOT / "packages" / "callqa"
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="callqa", description="Call center QA pipeline")
    parser.add_argument("--config", default=None, help="Config YAML path")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("fetch", help="Download recordings and build manifest")
    p_trans = sub.add_parser("transcribe", help="Transcribe a batch")
    p_trans.add_argument("--batch", type=int, required=True)
    p_trans.add_argument("--force", action="store_true")
    p_an = sub.add_parser("analyze", help="Analyze a batch with Claude")
    p_an.add_argument("--batch", type=int, required=True)
    p_an.add_argument("--force", action="store_true")
    p_rep = sub.add_parser("report", help="Generate Excel reports")
    p_rep.add_argument("--batch", type=int, default=None)
    p_rep.add_argument("--batch-only", action="store_true")
    sub.add_parser("run", help="Full pipeline (placeholder — use run_pipeline.sh)")

    args, extra = parser.parse_known_args(argv)
    cfg_path = args.config

    if args.command == "fetch":
        from callqa.ingestion.fetch import main as fetch_main
        cmd: list[str] = list(extra)
        if cfg_path:
            cmd = ["--config", cfg_path] + cmd
        fetch_main(cmd or None)
    elif args.command == "transcribe":
        from callqa.jobs.transcribe import main as transcribe_main
        cmd = []
        if cfg_path:
            cmd += ["--config", cfg_path]
        cmd += ["--batch", str(args.batch)]
        if args.force:
            cmd.append("--force")
        cmd += extra
        transcribe_main(cmd)
    elif args.command == "analyze":
        from callqa.jobs.analyze import main as analyze_main
        cmd = []
        if cfg_path:
            cmd += ["--config", cfg_path]
        cmd += ["--batch", str(args.batch)]
        if args.force:
            cmd.append("--force")
        cmd += extra
        analyze_main(cmd)
    elif args.command == "report":
        from callqa.jobs.report import main as report_main
        cmd = []
        if cfg_path:
            cmd += ["--config", cfg_path]
        if args.batch is not None:
            cmd += ["--batch", str(args.batch)]
        if args.batch_only:
            cmd.append("--batch-only")
        cmd += extra
        report_main(cmd)
    else:
        print("Use run_pipeline.sh for full multi-batch runs.")
        sys.exit(1)


if __name__ == "__main__":
    main()
