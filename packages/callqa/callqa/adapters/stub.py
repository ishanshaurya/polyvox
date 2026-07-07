"""Stub-fail adapter — empty transcript when all providers fail."""

from __future__ import annotations

from pathlib import Path

from callqa.transcription.types import TranscribeInfo, TranscribeResult, norm_lang


def transcribe(
    audio_path: Path,
    *,
    language_hint: str | None,
    prompt: str | None,
    cfg: dict,
) -> TranscribeResult:
    del audio_path, prompt, cfg
    hint = norm_lang(language_hint)
    return TranscribeResult(
        "",
        TranscribeInfo(language=hint, duration=None),
        None,
        None,
    )
