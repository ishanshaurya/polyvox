#!/usr/bin/env python3
"""Worker stub — will enqueue callqa pipeline steps per project workspace.

Phase 0: documents the contract. Phase 1: call packages/callqa jobs against
project.workspace_path (recordings/, outputs/).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PolyVox worker stub")
    parser.add_argument("--project-workspace", required=True, help="Path from API project.workspace_path")
    parser.add_argument(
        "--step",
        choices=["fetch", "transcribe", "analyze", "report", "all"],
        default="all",
    )
    args = parser.parse_args(argv)

    workspace = Path(args.project_workspace).resolve()
    if not workspace.is_dir():
        print(f"ERROR: workspace not found: {workspace}", file=sys.stderr)
        return 1

    print("PolyVox worker stub")
    print(f"  workspace: {workspace}")
    print(f"  step:      {args.step}")
    print()
    print("Not wired yet. Next: invoke callqa jobs with:")
    print(f"  recordings_folder = {workspace / 'recordings'}")
    print(f"  output_folder     = {workspace / 'outputs'}")
    print("See docs/ARCHITECTURE.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
