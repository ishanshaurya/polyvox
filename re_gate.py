"""Re-apply ASR gate to existing transcripts (no Whisper re-run)."""

from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401

from callqa.config.loader import load_config
from callqa.state import manifest, metadata
from callqa.transcription import asr_gate, normalize


def re_gate_batch(cfg: dict, batch: int | None = None) -> int:
    data = manifest.load(cfg)
    tx_dir = Path(cfg["output_folder"]) / "transcripts"
    updated = 0
    calls = manifest.calls_for_batch(data, batch) if batch else data.get("calls", [])
    for call in calls:
        stem = call.get("stem")
        if not stem:
            continue
        tx_path = tx_dir / f"{stem}.txt"
        if not tx_path.exists():
            continue
        meta = metadata.load_sidecar(cfg, stem) or {}
        raw = tx_path.read_text(encoding="utf-8")
        text = normalize.strip_prompt_echo(raw, cfg)
        if cfg.get("asr_dedupe_ngrams", True):
            text = normalize.dedupe_repeated_ngrams(text)
        lang = meta.get("language_hint") or meta.get("language")
        gate = asr_gate.evaluate(
            text,
            meta.get("duration_seconds"),
            meta.get("speech_duration_seconds"),
            cfg,
            language=lang,
        )
        meta["asr_pass"] = gate["pass"]
        meta["asr_metrics"] = gate["metrics"]
        meta["asr_reasons"] = gate.get("reasons", [])
        meta["unclear_recording"] = not gate["pass"]
        metadata.save_sidecar(cfg, stem, meta)
        manifest.update_call(
            data, stem,
            asr_pass=gate["pass"],
            asr_metrics=gate["metrics"],
            fields_populated=gate["fields_populated"],
            fields_blank=gate["fields_blank"],
        )
        updated += 1
        flag = "PASS" if gate["pass"] else "FAIL"
        print(f"  {stem}: {flag}  words={gate['metrics']['word_count']}")
    manifest.save(cfg, data)
    print(f"\n  Re-gated {updated} transcript(s)\n")
    return updated


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--batch", type=int, default=None)
    args = parser.parse_args()
    re_gate_batch(load_config(args.config), batch=args.batch)
