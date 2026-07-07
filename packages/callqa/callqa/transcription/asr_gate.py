"""ASR quality gate — single owner for pass/fail and metrics."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

# Devanagari, Telugu, Tamil
_TOKEN_RE = re.compile(r"[\w\u0900-\u097F\u0C00-\u0C7F\u0B80-\u0BFF'-]+", re.UNICODE)
_LATIN_WORD_RE = re.compile(r"^[a-zA-Z]+$")
_GIBBERISH_OK = frozenset({"a", "i"})
_INDIC_LANGS = frozenset({"te", "hi", "ta", "mr", "kn", "ml", "bn", "gu", "pa"})
_DYNAMIC_WPM_LANGS = frozenset({"te", "hi", "ta"})


def _wpm_for_duration(speech_secs: float) -> float:
    """Dynamic WPM floor by speech duration: b23=20, b46=25, b7p=35."""
    if speech_secs < 180:
        return 20.0
    if speech_secs < 360:
        return 25.0
    return 35.0


def _tokenize(text: str) -> list[str]:
    """Word tokens — strip punctuation so 'Namaste.' counts as a word."""
    return _TOKEN_RE.findall(text)


def _gibberish_score(tokens: list[str], *, language: str | None) -> float:
    """Fraction of Latin single-char noise tokens (English-aware)."""
    if not tokens:
        return 1.0
    lang = (language or "").lower()
    if lang in _INDIC_LANGS:
        return 0.0
    bad = sum(
        1
        for t in tokens
        if len(t) == 1 and t.isascii() and t.isalpha() and t.lower() not in _GIBBERISH_OK
    )
    return bad / len(tokens)


def _latin_ratio(tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    latin = sum(1 for t in tokens if _LATIN_WORD_RE.match(t))
    return latin / len(tokens)


def _repetition_score(tokens: list[str], n: int = 4) -> float:
    """Share of transcript covered by the most repeated n-gram."""
    if len(tokens) < n * 3:
        return 0.0
    ngrams = [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]
    top_count = Counter(ngrams).most_common(1)[0][1]
    return round((top_count * n) / len(tokens), 3)


def _lang_thresholds(cfg: dict, language: str | None) -> dict[str, float]:
    per_lang = cfg.get("asr_thresholds") or {}
    default = per_lang.get("default") or {
        "min_words": cfg.get("asr_min_words", 20),
        "max_gibberish": cfg.get("asr_max_gibberish_score", 0.25),
        "min_wpm": cfg.get("asr_min_wpm", 25),
        "max_repetition": cfg.get("asr_max_repetition", 0.25),
        "max_latin_ratio": cfg.get("asr_max_latin_ratio"),
    }
    key = (language or "").lower() or "default"
    merged = {**default, **per_lang.get(key, {})}
    return {k: float(v) if k != "min_words" else int(v) for k, v in merged.items()}


def evaluate(
    transcript: str,
    duration_seconds: float | None,
    cfg: dict,
    *,
    language: str | None = None,
    speech_duration_seconds: float | None = None,
) -> dict[str, Any]:
    """
    Return gate result: pass (bool), metrics dict, fields_populated / fields_blank hints.
    Language-aware thresholds (en / te / hi / ta) plus repetition and duration floor.
    WPM and duration_floor use speech_duration_seconds when set, else file duration.
    """
    text = (transcript or "").strip()
    words = _tokenize(text)
    word_count = len(words)

    file_duration = duration_seconds or 0.0
    speech_duration = speech_duration_seconds if speech_duration_seconds else file_duration
    wpm = round((word_count / speech_duration) * 60, 1) if speech_duration > 0 else 0.0
    gibberish = round(_gibberish_score(words, language=language), 3)
    repetition = _repetition_score(words, int(cfg.get("asr_repetition_ngram", 4)))
    latin_ratio = round(_latin_ratio(words), 3)

    thresholds = _lang_thresholds(cfg, language)
    lang = (language or "").lower()
    if lang in _DYNAMIC_WPM_LANGS and speech_duration > 0:
        wpm_floor = _wpm_for_duration(speech_duration)
        min_wpm = wpm_floor
    else:
        wpm_floor = float(cfg.get("asr_min_words_per_minute", 25))
        min_wpm = float(thresholds["min_wpm"])
    duration_floor = int((speech_duration / 60.0) * wpm_floor) if speech_duration > 0 else 0
    min_words = max(int(thresholds["min_words"]), duration_floor)
    max_gibberish = float(thresholds["max_gibberish"])
    max_repetition = float(thresholds.get("max_repetition", 0.25))
    max_latin_ratio = thresholds.get("max_latin_ratio")

    reasons = []
    if word_count < min_words:
        reasons.append(f"word_count={word_count}<{min_words}")
    if gibberish > max_gibberish:
        reasons.append(f"gibberish={gibberish}>{max_gibberish}")
    if speech_duration > 0 and wpm < min_wpm:
        reasons.append(f"wpm={wpm}<{min_wpm}")
    if repetition > max_repetition:
        reasons.append(f"repetition={repetition}>{max_repetition}")
    if lang in _INDIC_LANGS and max_latin_ratio is not None and latin_ratio > float(max_latin_ratio):
        reasons.append(f"latin_ratio={latin_ratio}>{max_latin_ratio}")

    passed = len(reasons) == 0
    metrics = {
        "word_count": word_count,
        "gibberish_score": gibberish,
        "wpm": wpm,
        "duration_seconds": file_duration,
        "speech_duration_seconds": round(speech_duration, 1) if speech_duration else 0.0,
        "repetition_score": repetition,
        "latin_ratio": latin_ratio,
        "min_words_effective": min_words,
        "language": lang or None,
    }

    if passed:
        populated = [
            "agent_name", "call_date", "call_outcome", "patient_issue",
            "kpi_scores", "complaints", "escalations", "qa_notes",
        ]
        blank = []
    else:
        populated = ["agent_name", "call_date", "call_outcome"]
        blank = [
            "patient_issue", "kpi_scores", "complaints",
            "escalations", "qa_notes",
        ]

    return {
        "pass": passed,
        "metrics": metrics,
        "reasons": reasons,
        "fields_populated": populated,
        "fields_blank": blank,
    }
