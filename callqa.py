#!/usr/bin/env python3
"""CLI entrypoint: python callqa.py fetch --config configs/june.yaml --dry-run"""

import _bootstrap  # noqa: F401
import sys
from pathlib import Path

_CLI_DIR = Path(__file__).resolve().parent / "apps" / "cli"
if str(_CLI_DIR) not in sys.path:
    sys.path.insert(0, str(_CLI_DIR))

from callqa_cli.__main__ import main

if __name__ == "__main__":
    main()
