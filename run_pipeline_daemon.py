#!/usr/bin/env python3
"""Run remaining pipeline batches — survives without tmux."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd: list[str]) -> int:
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    from pipeline_config import load_config

    cfg = load_config()
    num_batches = int(cfg["fetch_limit"]) // int(cfg["batch_size"])
    errors = 0
    for n in range(1, num_batches + 1):
        print(f"\n=== BATCH {n} ===", flush=True)
        if run([sys.executable, "1_transcribe.py", "--batch", str(n)]) != 0:
            errors += 1
            print(f"WARN: transcribe batch {n} had errors", flush=True)
        if run([sys.executable, "2_analyze.py", "--batch", str(n)]) != 0:
            errors += 1
            print(f"WARN: analyze batch {n} had errors", flush=True)
    if run([sys.executable, "3_report.py", "--batch", str(num_batches)]) != 0:
        errors += 1
    print("\nPIPELINE COMPLETE", flush=True)
    return errors


if __name__ == "__main__":
    raise SystemExit(main())
