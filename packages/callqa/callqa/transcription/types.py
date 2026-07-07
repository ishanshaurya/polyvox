"""Shared transcription result types and audio helpers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TranscribeInfo:
    language: str | None
    duration: float | None


@dataclass
class TranscribeResult:
    text: str
    info: TranscribeInfo
    file_duration: float | None
    active_seconds: float | None


def norm_lang(lang: str | None) -> str | None:
    if not lang:
        return None
    low = lang.lower()
    if low.startswith("eng"):
        return "en"
    if low.startswith("tel"):
        return "te"
    if low.startswith("hin"):
        return "hi"
    return low[:2] if len(low) >= 2 else low


def audio_duration_seconds(audio_path: Path) -> float | None:
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return round(float(out), 1) if out else None
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return None


def active_seconds_from_segments(segments) -> float | None:
    total = 0.0
    for seg in segments or []:
        start = getattr(seg, "start", None)
        end = getattr(seg, "end", None)
        if start is None and isinstance(seg, dict):
            start, end = seg.get("start"), seg.get("end")
        if end is not None and start is not None:
            total += max(0.0, float(end) - float(start))
    return round(total, 1) if total > 0 else None
