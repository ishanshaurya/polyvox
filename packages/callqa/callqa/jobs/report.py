"""Step 3: Generate Excel QA reports from analysis JSON."""

from __future__ import annotations

import argparse

from callqa.config.loader import load_config
from callqa.reports.excel_legacy import generate_reports
from callqa.reports.templates_v1 import generate as generate_templates_v1


def generate(cfg: dict, *, batch: int | None = None, batch_only: bool = False) -> None:
    template = (cfg.get("report_template") or "templates_v1").lower()
    if template == "templates_v1":
        generate_templates_v1(cfg, batch=batch, batch_only=batch_only)
    else:
        generate_reports(cfg)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--batch", type=int, default=None)
    parser.add_argument("--batch-only", action="store_true")
    args = parser.parse_args(argv)
    generate(load_config(args.config), batch=args.batch, batch_only=args.batch_only)
