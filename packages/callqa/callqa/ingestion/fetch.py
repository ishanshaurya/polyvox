"""Step 0: Select calls from CSV/XLSX CDR, download MP3s, write manifest."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import math
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests

from callqa.config.loader import load_config
from callqa.state import disposition, manifest, metadata


def talk_time_seconds(raw) -> int:
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return 0
    if isinstance(raw, dt.time):
        return raw.hour * 3600 + raw.minute * 60 + raw.second
    if isinstance(raw, (int, float)):
        return int(raw)
    raw = str(raw).strip()
    if not raw:
        return 0
    parts = raw.split(":")
    try:
        if len(parts) == 3:
            h, m, s = (int(float(p)) for p in parts)
            return h * 3600 + m * 60 + s
        if len(parts) == 2:
            m, s = (int(float(p)) for p in parts)
            return m * 60 + s
        return int(float(raw))
    except ValueError:
        return 0


def format_talk_time(raw) -> str:
    secs = talk_time_seconds(raw)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def parse_call_date(raw) -> date | None:
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if hasattr(raw, "to_pydatetime"):
        return raw.to_pydatetime().date()
    text = str(raw).strip()[:10]
    if re.match(r"^\d{2}-\d{2}-\d{4}$", text):
        d, m, y = text.split("-")
        return date(int(y), int(m), int(d))
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        y, m, d = text.split("-")
        return date(int(y), int(m), int(d))
    return None


def normalize_call_date(raw) -> str:
    parsed = parse_call_date(raw)
    if parsed:
        return parsed.isoformat()
    text = (str(raw) if raw is not None else "").strip()[:10]
    return text.replace("/", "-")[:10] or "unknown-date"


def _parse_cohort_bound(raw: str | None) -> date | None:
    if not raw:
        return None
    return parse_call_date(str(raw).strip())


def row_in_cohort_dates(row: dict, cfg: dict) -> bool:
    date_from = _parse_cohort_bound(cfg.get("cohort_date_from"))
    date_to = _parse_cohort_bound(cfg.get("cohort_date_to"))
    if not date_from and not date_to:
        return True
    call_date = parse_call_date(row.get("Call Date"))
    if call_date is None:
        return False
    if date_from and call_date < date_from:
        return False
    if date_to and call_date > date_to:
        return False
    return True


def _cell_str(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    if isinstance(value, dt.time):
        return format_talk_time(value)
    if isinstance(value, (datetime, date)):
        return normalize_call_date(value)
    return str(value).strip()


def normalize_xlsx_row(row: dict) -> dict:
    out: dict[str, str] = {}
    for key, value in row.items():
        if key == "Call Date":
            out[key] = normalize_call_date(value)
        elif key == "Talk Time":
            out[key] = format_talk_time(value)
        elif key == "Call ID":
            if value is None or (isinstance(value, float) and math.isnan(value)):
                out[key] = ""
            else:
                out[key] = str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)
        else:
            out[key] = _cell_str(value)
    return out


def last_arrow_agent(call_flow: str) -> str:
    if not call_flow:
        return ""
    parts = [p.strip() for p in str(call_flow).split("->")]
    for part in reversed(parts):
        match = re.search(r"Agent Dials \(([^)]+)\)", part)
        if match:
            return match.group(1).strip()
        if (
            re.match(r"^[A-Za-z].{1,60}$", part)
            and "Transfer" not in part
            and "Phone" not in part
            and "Queue" not in part
        ):
            return part.strip()
    return ""


def resolve_final_agent(row: dict, cleaned_column: str | None = None) -> str:
    if cleaned_column:
        cleaned = (row.get(cleaned_column) or "").strip()
        if cleaned and cleaned.upper() not in {"NA", "N/A", "-"}:
            return cleaned
    arrow_agent = last_arrow_agent(row.get("Call Flow") or "")
    if arrow_agent:
        return arrow_agent
    return (row.get("Agent") or "").strip()


def _detect_cleaned_agent_column(columns) -> str | None:
    for col in columns:
        label = str(col).strip().lower()
        if label in {"agent (cleaned)", "agent_cleaned", "agent cleaned"}:
            return str(col)
    return None


def _apply_agent_aliases(agent: str, cfg: dict) -> str:
    aliases = cfg.get("agent_name_aliases") or {}
    return aliases.get(agent, agent)


def _load_xlsx_rows(path: str, sheet, cfg: dict) -> list[dict]:
    df = pd.read_excel(path, sheet_name=sheet)
    cleaned_column = _detect_cleaned_agent_column(df.columns)
    rows: list[dict] = []
    for raw in df.to_dict(orient="records"):
        row = normalize_xlsx_row(raw)
        final_agent = resolve_final_agent(row, cleaned_column)
        row["Agent"] = _apply_agent_aliases(final_agent, cfg)
        row["_source_agent_raw"] = _cell_str(raw.get("Agent"))
        rows.append(row)
    return rows


def _load_single_cdr_source(source: dict | str, cfg: dict) -> list[dict]:
    if isinstance(source, str):
        path = source
        sheet = cfg.get("cdr_sheet", 0)
        fmt = (cfg.get("cdr_format") or "csv").lower()
    else:
        path = source["path"]
        sheet = source.get("sheet", cfg.get("cdr_sheet", 0))
        fmt = (source.get("format") or cfg.get("cdr_format") or "xlsx").lower()

    if fmt == "xlsx":
        return _load_xlsx_rows(path, sheet, cfg)
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.DictReader(f))
    if cfg.get("match_final_agent"):
        for row in rows:
            row["Agent"] = _apply_agent_aliases(resolve_final_agent(row), cfg)
    return rows


def load_cdr_rows(cfg: dict) -> list[dict]:
    sources = cfg.get("cdr_sources")
    if sources:
        rows: list[dict] = []
        for source in sources:
            rows.extend(_load_single_cdr_source(source, cfg))
        if cfg.get("cohort_date_from") or cfg.get("cohort_date_to"):
            rows = [r for r in rows if row_in_cohort_dates(r, cfg)]
        return rows

    path = cfg.get("cdr_path") or cfg.get("csv_path")
    if not path:
        raise SystemExit("\nERROR: config must set cdr_path, csv_path, or cdr_sources.\n")
    rows = _load_single_cdr_source(path, cfg)
    if cfg.get("cohort_date_from") or cfg.get("cohort_date_to"):
        rows = [r for r in rows if row_in_cohort_dates(r, cfg)]
    return rows


def normalize_recording_url(raw) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    for part in text.split(","):
        url = part.strip()
        if url.lower().endswith(".mp3"):
            return url
    return text.split(",")[0].strip()


def row_passes_filters(row: dict, cfg: dict | None = None) -> bool:
    cfg = cfg or {}
    if row.get("Status") != "Answered":
        return False
    url = normalize_recording_url(row.get("Recording URL"))
    if not url.lower().endswith(".mp3"):
        return False
    agent = row.get("Agent") or ""
    if not agent:
        return False
    if not cfg.get("match_final_agent"):
        if " -> " in agent:
            return False
        if "Transfer" in (row.get("Call Flow") or ""):
            return False
    if talk_time_seconds(row.get("Talk Time", "")) <= 0:
        return False
    return True


def bucket_for_seconds(seconds: int, buckets: dict) -> str | None:
    for name, (lo, hi) in buckets.items():
        if lo <= seconds <= hi:
            return name
    return None


def call_id8(call_id: str) -> str:
    return hashlib.md5(call_id.encode()).hexdigest()[:8]


def unique_key_for_row(row: dict) -> str:
    url = normalize_recording_url(row.get("Recording URL"))
    if url:
        return hashlib.md5(url.encode()).hexdigest()[:8]
    return call_id8(row.get("Call ID", ""))


def build_stem(agent: str, bucket: str, call_date: str, row: dict) -> str:
    slug = manifest.agent_slug(agent)
    date_norm = normalize_call_date(call_date)
    return f"{slug}_{bucket}_{date_norm}_{unique_key_for_row(row)}"


def _pick_spread(candidates: list[dict], n: int, *, seen: set[str]) -> list[dict]:
    if n <= 0 or not candidates:
        return []
    cands = sorted(candidates, key=lambda r: talk_time_seconds(r.get("Talk Time", "")))
    uniq: list[dict] = []
    local_seen: set[str] = set()
    for row in cands:
        uk = unique_key_for_row(row)
        if uk in seen or uk in local_seen:
            continue
        local_seen.add(uk)
        uniq.append(row)
    cands = uniq
    if not cands:
        return []
    if n >= len(cands):
        return cands
    picks: list[dict] = []
    used_idx: set[int] = set()
    for k in range(n):
        frac = (k + 1) / (n + 1)
        idx = int(round(frac * (len(cands) - 1)))
        while idx in used_idx and idx + 1 < len(cands):
            idx += 1
        while idx in used_idx and idx - 1 >= 0:
            idx -= 1
        if idx in used_idx:
            continue
        used_idx.add(idx)
        picks.append(cands[idx])
    return picks


def select_calls_per_agent(rows: list[dict], cfg: dict) -> list[dict]:
    agents = cfg["pilot_agents"]
    per_agent = int(cfg.get("calls_per_agent", 10))
    buckets = cfg.get("duration_buckets") or {}
    bucket_order = list(buckets.keys())
    calls_per_bucket = cfg.get("calls_per_bucket") or {}

    by_agent: dict[str, list[dict]] = {}
    for row in rows:
        agent = row.get("Agent", "")
        if agent not in agents:
            continue
        if not row_passes_filters(row, cfg):
            continue
        by_agent.setdefault(agent, []).append(row)

    selected: list[dict] = []
    seen_keys: set[str] = set()

    for agent in agents:
        candidates = by_agent.get(agent, [])
        if not candidates:
            continue
        agent_picks: list[dict] = []
        for bucket_name in bucket_order:
            want_n = int(calls_per_bucket.get(bucket_name, 0) or 0)
            if want_n <= 0:
                continue
            bucket_rows = [
                row for row in candidates
                if bucket_for_seconds(talk_time_seconds(row.get("Talk Time", "")), buckets) == bucket_name
            ]
            picks = _pick_spread(bucket_rows, want_n, seen=seen_keys)
            agent_picks.extend(picks)
            for pick in picks:
                seen_keys.add(unique_key_for_row(pick))

        remaining = per_agent - len(agent_picks)
        if remaining > 0:
            leftover = [row for row in candidates if unique_key_for_row(row) not in seen_keys]
            picks = _pick_spread(leftover, remaining, seen=seen_keys)
            agent_picks.extend(picks)
            for pick in picks:
                seen_keys.add(unique_key_for_row(pick))

        for row in agent_picks[:per_agent]:
            secs = talk_time_seconds(row.get("Talk Time", ""))
            bucket = bucket_for_seconds(secs, buckets) if buckets else "any"
            selected.append({
                **row,
                "_bucket": bucket or "any",
                "_talk_secs": secs,
            })

    limit = int(cfg.get("fetch_limit", len(selected)))
    return selected[:limit]


def select_calls(rows: list[dict], cfg: dict) -> list[dict]:
    if cfg.get("selection_mode") == "per_agent":
        return select_calls_per_agent(rows, cfg)

    agents = cfg["pilot_agents"]
    buckets = cfg["duration_buckets"]
    limit = int(cfg.get("fetch_limit", 9))
    bucket_order = list(buckets.keys())
    calls_per_bucket = cfg.get("calls_per_bucket") or {b: 1 for b in bucket_order}

    by_agent_bucket: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        agent = row.get("Agent", "")
        if agent not in agents:
            continue
        if not row_passes_filters(row, cfg):
            continue
        secs = talk_time_seconds(row.get("Talk Time", ""))
        bucket = bucket_for_seconds(secs, buckets)
        if not bucket:
            continue
        key = (agent, bucket)
        by_agent_bucket.setdefault(key, []).append(row)

    selected: list[dict] = []
    seen_keys: set[str] = set()

    for bucket_name in bucket_order:
        want_n = int(calls_per_bucket.get(bucket_name, 1) or 1)
        for agent in agents:
            if len(selected) >= limit:
                break
            key = (agent, bucket_name)
            candidates = by_agent_bucket.get(key, [])
            if not candidates:
                continue
            picks = _pick_spread(candidates, want_n, seen=seen_keys)
            for row in picks:
                if len(selected) >= limit:
                    break
                uk = unique_key_for_row(row)
                if uk in seen_keys:
                    continue
                seen_keys.add(uk)
                selected.append({
                    **row,
                    "_bucket": bucket_name,
                    "_talk_secs": talk_time_seconds(row.get("Talk Time", "")),
                })
        if len(selected) >= limit:
            break

    return selected[:limit]


def download_mp3(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return
    url = normalize_recording_url(url)
    resp = requests.get(url, timeout=120, stream=True)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)


def run_fetch(cfg: dict, *, dry_run: bool = False) -> None:
    if cfg.get("cdr_sources"):
        source_path = ", ".join(
            s["path"] if isinstance(s, dict) else str(s) for s in cfg["cdr_sources"]
        )
    else:
        source_path = cfg.get("cdr_path") or cfg.get("csv_path")
    rec_dir = Path(cfg["recordings_folder"])
    batch_size = int(cfg.get("batch_size", 4))

    print(f"\n  Reading CDR: {source_path}")
    rows = load_cdr_rows(cfg)
    print(f"  Rows after date filter: {len(rows)}")

    picked = select_calls(rows, cfg)
    if not picked:
        print("  No calls matched selection filters.\n")
        return

    print(f"  Selected {len(picked)} call(s)\n")

    manifest_calls = []
    for i, row in enumerate(picked):
        agent = row["Agent"]
        bucket = row["_bucket"]
        call_id = row.get("Call ID", "")
        call_date = normalize_call_date(row.get("Call Date", ""))
        stem = build_stem(agent, bucket, call_date, row)
        batch = i // batch_size + 1
        disp = row.get("Disposition", "")
        outcome = disposition.disposition_to_outcome(disp, cfg)

        meta = {
            "stem": stem,
            "call_id": call_id,
            "agent_name": agent,
            "agent_id": row.get("Agent ID", ""),
            "center": row.get("Location", ""),
            "hospital": cfg.get("site_name") or cfg.get("hospital_name") or "Acme Org",
            "site": cfg.get("site_name") or cfg.get("hospital_name") or "Acme Org",
            "call_date": call_date,
            "talk_time": row.get("Talk Time", ""),
            "talk_time_seconds": row["_talk_secs"],
            "duration_bucket": bucket,
            "disposition": disp,
            "call_outcome": outcome,
            "recording_url": normalize_recording_url(row.get("Recording URL", "")),
            "call_flow": row.get("Call Flow", ""),
            "status_csv": row.get("Status", ""),
            "filename": f"{stem}.mp3",
        }

        mp3_path = rec_dir / f"{stem}.mp3"
        if dry_run:
            print(f"  [dry-run] {stem}  batch={batch}  {agent}  {bucket}")
        else:
            print(f"  Downloading {stem}.mp3 ...")
            download_mp3(meta["recording_url"], mp3_path)
            meta["audio_path"] = str(mp3_path.resolve())
            metadata.save_sidecar(cfg, stem, meta)

        manifest_calls.append({
            "stem": stem,
            "call_id": call_id,
            "agent_name": agent,
            "duration_bucket": bucket,
            "batch": batch,
            "status": "downloaded",
            "asr_pass": None,
            "asr_metrics": {"word_count": 0, "gibberish_score": None, "wpm": None},
            "fields_populated": ["agent_name", "call_date", "call_outcome"],
            "fields_blank": [
                "patient_issue", "kpi_scores", "complaints",
                "escalations", "qa_notes",
            ],
        })

    if not dry_run:
        data = {
            "created_at": datetime.now().isoformat(),
            "csv_path": source_path,
            "calls": manifest_calls,
        }
        manifest.save(cfg, data)
        print(f"\n  Manifest: {manifest.manifest_path(cfg)}")
        print(f"  Recordings: {rec_dir.resolve()}\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Fetch pilot calls from CDR")
    parser.add_argument("--config", default=None, help="Config YAML")
    parser.add_argument("--dry-run", action="store_true", help="Select only, no download")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    run_fetch(cfg, dry_run=args.dry_run)
