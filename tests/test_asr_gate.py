"""Regression harness for ASR gate — dynamic WPM + cascade accept logic."""

from __future__ import annotations

import json
from pathlib import Path

import _bootstrap  # noqa: F401

from callqa.config.loader import load_config
from callqa.transcription import asr_gate, normalize
from callqa.transcription.engine import attempt_acceptable

LEGACY_EXPECTED = {
    "Suneetha_Aithabathula_b23_2026-05-04_0c6d00d9": True,
    "Nayak_Jaisree_b23_2026-05-03_85d4af70": True,
    "Jennifer_Franchise_Pillay_b23_2026-05-20_d8f3d9a9": False,
    "Venkata_Nagalakshmi_b23_2026-05-03_85d4af70": False,
}

FIXTURES_PATH = Path(__file__).with_name("test_asr_fixtures.json")

DYNAMIC_WPM_CASES = [
    {"lang": "te", "speech_secs": 150, "words": 50, "want_pass_wpm": True},   # b23 floor 20
    {"lang": "te", "speech_secs": 150, "words": 40, "want_pass_wpm": False},
    {"lang": "te", "speech_secs": 300, "words": 130, "want_pass_wpm": True},  # b46 floor 25
    {"lang": "te", "speech_secs": 420, "words": 250, "want_pass_wpm": True},  # b7p floor 35
    {"lang": "en", "speech_secs": 150, "words": 63, "want_pass_wpm": True},   # static 25 wpm
]

CASCADE_ACCEPT_CASES = [
    {
        "name": "te_hint_high_latin_needs_fallback",
        "lang_hint": "te",
        "latin_ratio": 0.75,
        "pass_gate": True,
        "want_acceptable": False,
    },
    {
        "name": "te_hint_good_latin_ok",
        "lang_hint": "te",
        "latin_ratio": 0.20,
        "pass_gate": True,
        "want_acceptable": True,
    },
    {
        "name": "gate_fail_not_acceptable",
        "lang_hint": "te",
        "latin_ratio": 0.10,
        "pass_gate": False,
        "want_acceptable": False,
    },
]


def run_fixture_harness(cfg: dict) -> int:
    if not FIXTURES_PATH.exists():
        print(f"  [SKIP] No fixtures at {FIXTURES_PATH}")
        return 0
    fixtures = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    failures = 0
    for stem, fx in fixtures.items():
        text = fx["text"]
        lang = fx.get("language")
        duration = fx.get("duration")
        want_pass = fx["want_pass"]
        result = asr_gate.evaluate(text, duration, cfg, language=lang)
        got = result["pass"]
        ok = got == want_pass
        flag = "OK" if ok else "FAIL"
        print(
            f"  [{flag}] {stem}: want={want_pass} got={got} "
            f"lang={lang} reasons={result.get('reasons')} metrics={result['metrics']}"
        )
        if not ok:
            failures += 1
    return failures


def run_legacy_harness(cfg: dict) -> int:
    base = Path(cfg["output_folder"])
    failures = 0
    for stem, want_pass in LEGACY_EXPECTED.items():
        meta_path = base / "metadata" / f"{stem}.json"
        tx_path = base / "transcripts" / f"{stem}.txt"
        if not meta_path.exists() or not tx_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        text = tx_path.read_text(encoding="utf-8")
        text = normalize.strip_prompt_echo(text, cfg)
        text = normalize.dedupe_hold_phrases(text)
        if cfg.get("asr_dedupe_ngrams", True):
            text = normalize.dedupe_repeated_ngrams(text)
        lang = meta.get("language")
        duration = meta.get("duration_seconds")
        result = asr_gate.evaluate(text, duration, cfg, language=lang)
        got = result["pass"]
        ok = got == want_pass
        flag = "OK" if ok else "FAIL"
        print(
            f"  [{flag}] {stem}: want={want_pass} got={got} "
            f"lang={lang} reasons={result.get('reasons')}"
        )
        if not ok:
            failures += 1
    return failures


def run_dynamic_wpm_harness(cfg: dict) -> int:
    failures = 0
    for case in DYNAMIC_WPM_CASES:
        speech = case["speech_secs"]
        wpm = round((case["words"] / speech) * 60, 1)
        filler = "word " * case["words"]
        result = asr_gate.evaluate(
            filler.strip(),
            speech,
            cfg,
            language=case["lang"],
            speech_duration_seconds=speech,
        )
        wpm_reason = any(r.startswith("wpm=") for r in result.get("reasons", []))
        got = not wpm_reason
        ok = got == case["want_pass_wpm"]
        flag = "OK" if ok else "FAIL"
        print(
            f"  [{flag}] dynamic_wpm lang={case['lang']} speech={speech}s "
            f"words={case['words']} wpm={wpm} want_pass={case['want_pass_wpm']} got={got}"
        )
        if not ok:
            failures += 1
    return failures


def run_cascade_accept_harness() -> int:
    failures = 0
    for case in CASCADE_ACCEPT_CASES:
        gate = {
            "pass": case["pass_gate"],
            "metrics": {"latin_ratio": case["latin_ratio"]},
        }
        got = attempt_acceptable(gate, case["lang_hint"])
        ok = got == case["want_acceptable"]
        flag = "OK" if ok else "FAIL"
        print(
            f"  [{flag}] cascade {case['name']}: "
            f"want_acceptable={case['want_acceptable']} got={got}"
        )
        if not ok:
            failures += 1
    return failures


def run_harness() -> int:
    cfg = load_config()
    print("\n  ASR gate fixtures (2026-06-17 unclear + scored):")
    n = run_fixture_harness(cfg)
    print("\n  Dynamic WPM (te/hi/ta tiers 20/25/35):")
    n += run_dynamic_wpm_harness(cfg)
    print("\n  Cascade accept logic (single-attempt, high-latin cutoff 0.70):")
    n += run_cascade_accept_harness()
    print("\n  Legacy pilot stems (if artifacts present):")
    n += run_legacy_harness(cfg)
    return n


if __name__ == "__main__":
    failures = run_harness()
    if failures:
        print(f"\n  {failures} harness failure(s)\n")
        raise SystemExit(1)
    print("\n  All ASR gate expectations met.\n")
