"""Step 2: Analyze transcripts with Claude (profile from config)."""

from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import anthropic

from callqa.analysis.profiles import get_profile
from callqa.analysis.scorer import (
    build_asr_fail_stub,
    extract_json,
    score_to_stars,
    weighted_overall,
)
from callqa.config.loader import ensure_api_key, load_config
from callqa.state import manifest, metadata


def analyze_batch(
    cfg: dict,
    batch: int,
    *,
    force: bool = False,
    stems: set[str] | None = None,
    ignore_asr_gate: bool = False,
) -> int:
    data = manifest.load(cfg)
    claude_pending = manifest.pending_analysis(data, batch, ignore_asr_gate=ignore_asr_gate)
    stub_pending = [] if ignore_asr_gate else manifest.pending_asr_stubs(data, batch)

    if stems:
        claude_pending = [c for c in claude_pending if c.get("stem") in stems]
        stub_pending = [c for c in stub_pending if c.get("stem") in stems]

    analysis_dir = os.path.join(cfg["output_folder"], "analysis")
    os.makedirs(analysis_dir, exist_ok=True)

    def _needs_work(call: dict) -> bool:
        if force:
            return True
        return not os.path.exists(os.path.join(analysis_dir, f"{call['stem']}.json"))

    claude_pending = [c for c in claude_pending if _needs_work(c)]
    stub_pending = [c for c in stub_pending if _needs_work(c)]

    if not claude_pending and not stub_pending:
        print(f"\n  Batch {batch}: nothing pending for analysis.\n")
        return 0

    done = errors = stubs = 0

    for call in stub_pending:
        stem = call["stem"]
        meta = metadata.resolve(cfg, stem)
        result = build_asr_fail_stub(meta, cfg, stem)
        out_path = os.path.join(analysis_dir, f"{stem}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        manifest.update_call(data, stem, status="analyzed")
        print(f"  ○ {stem}  [{meta.get('agent_name')}]  ASR stub (no Claude)")
        stubs += 1

    if not claude_pending:
        manifest.save(cfg, data)
        print("-" * 60)
        print(f"  Analysis complete: {stubs} stub(s), 0 Claude, {errors} errors\n")
        return stubs

    ensure_api_key(cfg)
    profile = get_profile(cfg)
    model = cfg.get("claude_model", "claude-sonnet-4-5")
    client = anthropic.Anthropic()
    system_prompt = profile.build_system_prompt(cfg)
    transcript_dir = os.path.join(cfg["output_folder"], "transcripts")
    max_workers = int(cfg.get("analysis_workers", 3))

    print(f"\n  Batch {batch}: Claude on {len(claude_pending)} call(s), stubs already: {stubs}\n")

    def process_one(call: dict):
        stem = call["stem"]
        out_path = os.path.join(analysis_dir, f"{stem}.json")

        tp = os.path.join(transcript_dir, f"{stem}.txt")
        with open(tp, encoding="utf-8") as f:
            transcript_text = f.read().strip()

        meta = metadata.resolve(cfg, stem)
        unclear = False if ignore_asr_gate else not call.get("asr_pass", True)
        prompt = profile.build_user_prompt(
            transcript_text,
            meta.get("filename", f"{stem}.mp3"),
            meta.get("agent_name", "Unknown"),
            cfg,
            hospital=meta.get("hospital", ""),
            call_date=meta.get("call_date", ""),
            csv_call_outcome=meta.get("call_outcome", ""),
            csv_disposition=meta.get("disposition", ""),
            unclear=unclear,
        )

        last_err = None
        raw = None
        for attempt in range(3):
            try:
                response = client.messages.create(
                    model=model,
                    max_tokens=3500,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = response.content[0].text
                result = extract_json(raw)

                result["call_outcome"] = meta.get("call_outcome", result.get("csv_call_outcome", ""))
                result["filename"] = meta.get("filename", f"{stem}.mp3")
                result["agent_name"] = meta.get("agent_name", result.get("agent_name", ""))
                result["hospital"] = meta.get("hospital", "")
                result["call_date"] = meta.get("call_date", "")

                if unclear:
                    result["unclear_recording"] = True
                    result["patient_issue"] = ""
                    result["kpi_scores"] = {k["name"]: None for k in cfg["kpis"]}
                    result["overall_score"] = None
                    result["star_rating"] = None
                else:
                    kpi = result.get("kpi_scores") or {}
                    overall = result.get("overall_score")
                    if overall in (None, ""):
                        overall = weighted_overall(kpi, cfg)
                    if overall is not None:
                        result["overall_score"] = overall
                        result["star_rating"] = score_to_stars(float(overall), cfg)

                result["analyzed_at"] = datetime.now().isoformat()
                result["_tokens"] = {
                    "input": getattr(response.usage, "input_tokens", 0),
                    "output": getattr(response.usage, "output_tokens", 0),
                }

                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                manifest.update_call(data, stem, status="analyzed")
                return ("ok", stem, result)
            except json.JSONDecodeError as e:
                last_err = f"JSON parse: {e}"
                break
            except Exception as e:
                last_err = str(e)
                if attempt < 2:
                    time.sleep(2 ** attempt)

        if raw:
            with open(os.path.join(analysis_dir, f"{stem}_error.txt"), "w", encoding="utf-8") as f:
                f.write(raw)
        return ("err", stem, last_err)

    done = errors = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(process_one, c): c for c in claude_pending}
        for fut in as_completed(futures):
            status, stem, payload = fut.result()
            if status == "ok":
                r = payload
                overall = r.get("overall_score")
                print(f"  ✓ {stem}  [{r.get('agent_name')}]  {overall or 'n/a'}/100")
                done += 1
            elif status == "err":
                print(f"  ✗ {stem}  ERROR: {payload}")
                errors += 1

    manifest.save(cfg, data)
    print("-" * 60)
    print(f"  Analysis complete: {done} Claude, {stubs} stub(s), {errors} errors\n")
    return done + stubs


def _parse_stems(raw: list[str]) -> set[str] | None:
    if not raw:
        return None
    out: set[str] = set()
    for item in raw:
        for part in item.split(","):
            part = part.strip()
            if part:
                out.add(part)
    return out or None


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--batch", type=int, required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--stem", action="append", default=[])
    parser.add_argument("--ignore-asr-gate", action="store_true")
    args = parser.parse_args(argv)
    analyze_batch(
        load_config(args.config),
        args.batch,
        force=args.force,
        stems=_parse_stems(args.stem),
        ignore_asr_gate=args.ignore_asr_gate,
    )
