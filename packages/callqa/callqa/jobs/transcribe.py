"""Step 1: Transcribe MP3 recordings via TranscriptionEngine cascade."""

from __future__ import annotations

import argparse
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from callqa.config.loader import load_config, resolve_assemblyai_api_key, resolve_groq_api_key
from callqa.state import manifest, metadata
from callqa.transcription.asr_gate import evaluate as asr_evaluate
from callqa.transcription.engine import TranscriptionEngine
from callqa.transcription.types import TranscribeInfo, TranscribeResult, norm_lang


def _language_hint(cfg: dict, agent_name: str) -> str | None:
    if cfg.get("whisper_language"):
        return cfg.get("whisper_language")
    hints = cfg.get("agent_language_hints") or {}
    return hints.get(agent_name)


def _transcribe_one(
    call: dict,
    *,
    cfg: dict,
    rec_dir: Path,
    transcript_dir: str,
    engine: TranscriptionEngine,
    manifest_data: dict,
    manifest_lock: threading.Lock,
) -> tuple[str, str | None]:
    stem = call["stem"]
    audio_path = rec_dir / f"{stem}.mp3"
    if not audio_path.exists():
        print(f"  SKIP {stem}: MP3 missing at {audio_path}")
        return "skip", stem

    meta = metadata.resolve(cfg, stem, str(audio_path))
    transcript_path = os.path.join(transcript_dir, f"{stem}.txt")
    agent_name = meta.get("agent_name", "")
    lang_hint = _language_hint(cfg, agent_name)
    hint = norm_lang(lang_hint)

    print(f"  Transcribing: {stem}  [{agent_name}]  hint={hint or 'auto'}")

    try:
        outcome = engine.transcribe_call(audio_path, language_hint=lang_hint)
        transcript_text = outcome.text
        gate = outcome.gate
        result = outcome.result
        lang_used = outcome.lang_used
        provider = outcome.provider
        asr_attempts = outcome.asr_attempts
        retried = outcome.retried
    except Exception as exc:
        print(f"  ERROR {stem}: {exc} — marking ASR fail, continuing")
        transcript_text = ""
        gate = asr_evaluate("", None, cfg, language=hint)
        gate["pass"] = False
        gate.setdefault("reasons", []).append(f"transcribe_error:{type(exc).__name__}")
        result = TranscribeResult("", TranscribeInfo(language=hint, duration=None), None, None)
        lang_used = hint
        provider = "error"
        asr_attempts = [{"provider": "error", "lang": hint, "pass": False, "reasons": gate["reasons"], "metrics": gate["metrics"]}]
        retried = False

    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript_text)

    meta.update({
        "transcribed_at": datetime.now().isoformat(),
        "language": lang_used or getattr(result.info, "language", None) or "unknown",
        "language_hint": hint,
        "asr_attempts": asr_attempts,
        "duration_seconds": result.file_duration,
        "speech_duration_seconds": result.active_seconds,
        "word_count": gate["metrics"]["word_count"],
        "asr_pass": gate["pass"],
        "asr_metrics": gate["metrics"],
        "asr_reasons": gate.get("reasons", []),
        "asr_retried": retried,
        "unclear_recording": not gate["pass"],
        "transcription_engine": provider,
        "transcription_cascade": engine.cascade,
    })
    metadata.save_sidecar(cfg, stem, meta)

    with manifest_lock:
        manifest.update_call(
            manifest_data, stem,
            status="transcribed",
            asr_pass=gate["pass"],
            asr_metrics=gate["metrics"],
            fields_populated=gate["fields_populated"],
            fields_blank=gate["fields_blank"],
        )
        manifest.save(cfg, manifest_data)

    flag = "" if gate["pass"] else "  [ASR FAIL]"
    retry_note = " (cascade)" if retried else ""
    speech = gate["metrics"].get("speech_duration_seconds", result.active_seconds)
    print(
        f"   Done  [{result.file_duration}s file, {speech}s speech, "
        f"{gate['metrics']['word_count']} words, "
        f"provider={provider}, lang={lang_used or '?'}]{retry_note}{flag}\n"
    )
    return "ok", stem


def transcribe_batch(
    cfg: dict,
    batch: int,
    *,
    force: bool = False,
    stems: set[str] | None = None,
    groq_model_override: str | None = None,
    cascade_from: str | None = None,
) -> int:
    data = manifest.load(cfg)
    if not data.get("calls"):
        print("\n  No manifest found. Run fetch first.\n")
        return 0

    pending = manifest.calls_for_batch(data, batch) if force else manifest.pending_transcription(data, batch)
    if stems:
        pending = [c for c in pending if c.get("stem") in stems]
    if not pending:
        msg = "no calls in manifest" if force else "no calls with status=downloaded"
        print(f"\n  Batch {batch}: {msg}.\n")
        return 0

    cascade = cfg.get("transcription_cascade") or ["assemblyai", "groq", "faster-whisper"]
    effective = list(cascade)
    if cascade_from:
        try:
            effective = cascade[cascade.index(cascade_from):]
        except ValueError:
            effective = [cascade_from]

    if "assemblyai" in effective and not resolve_assemblyai_api_key(cfg):
        print("\n  WARNING: ASSEMBLYAI_API_KEY not set — assemblyai steps will fail and cascade to Groq.\n")
    if "groq" in effective and not resolve_groq_api_key(cfg):
        print("\n  WARNING: GROQ_API_KEY not set — groq steps will fail and cascade to faster-whisper.\n")

    rec_dir = Path(cfg["recordings_folder"])
    transcript_dir = os.path.join(cfg["output_folder"], "transcripts")
    os.makedirs(transcript_dir, exist_ok=True)

    workers = int(cfg.get("transcription_workers", 3))
    whisper_lock = threading.Lock()
    engine = TranscriptionEngine(
        cfg,
        cascade_from=cascade_from,
        groq_model_override=groq_model_override,
        whisper_lock=whisper_lock,
    )
    manifest_lock = threading.Lock()

    print(f"\n  Batch {batch}: transcribing {len(pending)} call(s) "
          f"(workers={workers}, cascade={' → '.join(engine.cascade)})\n")

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                _transcribe_one,
                call,
                cfg=cfg,
                rec_dir=rec_dir,
                transcript_dir=transcript_dir,
                engine=engine,
                manifest_data=data,
                manifest_lock=manifest_lock,
            ): call
            for call in pending
        }
        for fut in as_completed(futures):
            status, _stem = fut.result()
            if status == "ok":
                done += 1

    print("-" * 60)
    print(f"  Transcription complete: {done} new for batch {batch}")
    print(f"  Review manifest before Claude: {manifest.manifest_path(cfg)}\n")
    return done


def mark_fail_stems(
    cfg: dict,
    stems: set[str],
    *,
    batch: int | None = None,
) -> int:
    data = manifest.load(cfg)
    if not data.get("calls"):
        print("\n  No manifest found. Run fetch first.\n")
        return 0

    transcript_dir = os.path.join(cfg["output_folder"], "transcripts")
    os.makedirs(transcript_dir, exist_ok=True)
    done = 0

    for stem in sorted(stems):
        call = manifest.find_call(data, stem)
        if call is None:
            print(f"  SKIP {stem}: not in manifest")
            continue
        if batch is not None and call.get("batch") != batch:
            print(f"  SKIP {stem}: not in batch {batch} (is batch {call.get('batch')})")
            continue

        rec_dir = Path(cfg["recordings_folder"])
        audio_path = rec_dir / f"{stem}.mp3"
        meta = metadata.resolve(cfg, stem, str(audio_path) if audio_path.exists() else stem)
        agent_name = meta.get("agent_name", "")
        hint = norm_lang(_language_hint(cfg, agent_name))
        transcript_path = os.path.join(transcript_dir, f"{stem}.txt")

        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write("")

        gate = asr_evaluate("", None, cfg, language=hint)
        gate["pass"] = False
        gate.setdefault("reasons", []).append("asr_unavailable")

        meta.update({
            "transcribed_at": datetime.now().isoformat(),
            "language": hint or "unknown",
            "language_hint": hint,
            "asr_attempts": [{"provider": "stub-fail", "lang": hint, "pass": False, "reasons": ["asr_unavailable"], "metrics": gate["metrics"]}],
            "duration_seconds": meta.get("duration_seconds"),
            "speech_duration_seconds": None,
            "word_count": 0,
            "asr_pass": False,
            "asr_metrics": gate["metrics"],
            "asr_reasons": gate["reasons"],
            "asr_retried": False,
            "unclear_recording": True,
            "transcription_engine": "stub-fail",
        })
        metadata.save_sidecar(cfg, stem, meta)

        manifest.update_call(
            data, stem,
            status="transcribed",
            asr_pass=False,
            asr_metrics=gate["metrics"],
            fields_populated=gate["fields_populated"],
            fields_blank=gate["fields_blank"],
        )
        manifest.save(cfg, data)
        print(f"  MARK-FAIL {stem}  [{agent_name}]  → transcribed, asr_pass=false")
        done += 1

    print(f"\n  Stub-failed {done} stem(s)\n")
    return done


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
    parser.add_argument("--batch", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--stem", action="append", default=[])
    parser.add_argument("--mark-fail", action="append", default=[])
    parser.add_argument("--groq-model", default=None)
    parser.add_argument("--cascade-from", default=None)
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    mark_stems = _parse_stems(args.mark_fail)
    if mark_stems:
        mark_fail_stems(cfg, mark_stems, batch=args.batch)
    elif args.batch is None:
        parser.error("--batch is required unless using --mark-fail")
    else:
        transcribe_batch(
            cfg,
            args.batch,
            force=args.force,
            stems=_parse_stems(args.stem),
            groq_model_override=args.groq_model,
            cascade_from=args.cascade_from,
        )
