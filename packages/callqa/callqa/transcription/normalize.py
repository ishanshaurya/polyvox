"""Transcript cleanup before ASR gate — prompt echo and repetition."""

from __future__ import annotations

import re
from collections import Counter

_ECHO_SPLIT_RE = re.compile(r"[.;]\s*")


def _echo_phrases(cfg: dict) -> list[str]:
    """Phrases from prompts that Whisper/Groq may leak on sparse audio."""
    phrases: set[str] = set()
    for key in ("whisper_initial_prompt",):
        raw = (cfg.get(key) or "").strip()
        if raw:
            phrases.add(raw)
            for part in _ECHO_SPLIT_RE.split(raw):
                part = part.strip(" ,")
                if len(part) >= 12:
                    phrases.add(part)
    for raw in (cfg.get("whisper_language_prompts") or {}).values():
        raw = (raw or "").strip()
        if raw:
            phrases.add(raw)
            for part in _ECHO_SPLIT_RE.split(raw):
                part = part.strip(" ,")
                if len(part) >= 12:
                    phrases.add(part)
    # Legacy tail that leaked before prompt shortening
    phrases.update({
        "Appointment booking, doctor names, locations",
        "Appointment booking, doctor names",
        "appointment booking, doctor names, locations",
        "Thank you for staying online",
        "Prayer of the Lord",
        "Praise our love",
        "When the children come below",
        "Can't I hear a song",
        "Rainbow Children Hospital Hindi English Telugu",
    })
    return sorted((p for p in phrases if p), key=len, reverse=True)


def dedupe_hold_phrases(text: str) -> str:
    """Collapse repeated hold-music / prayer fragments common on garbled calls."""
    if not text:
        return text
    patterns = [
        r"(?:Thank you\.?\s*){3,}",
        r"(?:Prayer of the Lord\.?\s*){2,}",
        r"(?:Praise our love[^.]*\.?\s*){2,}",
        r"(?:When the children come below[^.]*\.?\s*){2,}",
        r"(?:Rainbow Children(?:'s)? Hospital\.?\s*){3,}",
        r"(?:Hindi,?\s*English,?\s*Telugu\.?\s*){2,}",
        r"(?:Appointments,?\s*doctors,?\s*Hyderabad\.?\s*){2,}",
    ]
    result = text
    for pat in patterns:
        result = re.sub(pat, " ", result, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", result).strip()


def strip_prompt_echo(text: str, cfg: dict) -> str:
    """Remove leaked initial-prompt phrases (often repeated on hold/silence)."""
    result = (text or "").strip()
    if not result:
        return result
    for phrase in _echo_phrases(cfg):
        escaped = re.escape(phrase.strip())
        result = re.sub(
            rf"(?:\s*{escaped}\s*[\.,]?\s*){{2,}}",
            " ",
            result,
            flags=re.IGNORECASE,
        )
        result = re.sub(
            rf"^(?:\s*{escaped}\s*[\.,]?\s*)+",
            "",
            result,
            flags=re.IGNORECASE,
        )
        result = re.sub(
            rf"(?:\s*{escaped}\s*[\.,]?\s*)+$",
            "",
            result,
            flags=re.IGNORECASE,
        )
    return re.sub(r"\s+", " ", result).strip()


def dedupe_repeated_ngrams(text: str, n: int = 4, *, min_repeats: int = 3) -> str:
    """Collapse runs where the same n-gram repeats min_repeats+ times."""
    tokens = text.split()
    if len(tokens) < n * min_repeats:
        return text
    out: list[str] = []
    i = 0
    while i < len(tokens):
        if i + n * min_repeats <= len(tokens):
            gram = tuple(tokens[i : i + n])
            reps = 1
            j = i + n
            while j + n <= len(tokens) and tuple(tokens[j : j + n]) == gram:
                reps += 1
                j += n
            if reps >= min_repeats:
                out.extend(gram)
                i = j
                continue
        out.append(tokens[i])
        i += 1
    return " ".join(out)
