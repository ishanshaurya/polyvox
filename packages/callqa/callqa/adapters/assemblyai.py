"""AssemblyAI universal-3-pro / universal-2 adapter."""

from __future__ import annotations

from pathlib import Path

from callqa.config.loader import ensure_assemblyai_api_key
from callqa.transcription.types import (
    TranscribeInfo,
    TranscribeResult,
    active_seconds_from_segments,
    audio_duration_seconds,
    norm_lang,
)

_AAI_LANG = {"te": "te", "hi": "hi", "en": "en", "ta": "ta"}


def _active_from_words(words) -> float | None:
    if not words:
        return None
    total_ms = 0.0
    for word in words:
        start = getattr(word, "start", None)
        end = getattr(word, "end", None)
        if start is None and isinstance(word, dict):
            start, end = word.get("start"), word.get("end")
        if end is not None and start is not None:
            total_ms += max(0.0, float(end) - float(start))
    return round(total_ms / 1000.0, 1) if total_ms > 0 else None


def transcribe(
    audio_path: Path,
    *,
    language_hint: str | None,
    prompt: str | None,
    cfg: dict,
) -> TranscribeResult:
    try:
        import assemblyai as aai
    except ImportError:
        raise RuntimeError("assemblyai not installed — pip install assemblyai")

    ensure_assemblyai_api_key(cfg)
    models = cfg.get("assemblyai_speech_models") or ["universal-3-pro", "universal-2"]
    config_kw: dict = {"speech_models": list(models)}

    lang = norm_lang(language_hint)
    if lang:
        config_kw["language_code"] = _AAI_LANG.get(lang, lang)

    # keyterms_prompt and prompt are mutually exclusive on AssemblyAI
    keyterms = cfg.get("assemblyai_keyterms_prompt") or []
    if keyterms:
        config_kw["keyterms_prompt"] = list(keyterms)
    elif prompt:
        config_kw["prompt"] = prompt

    config = aai.TranscriptionConfig(**config_kw)
    transcript = aai.Transcriber().transcribe(str(audio_path), config=config)

    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"AssemblyAI transcription failed: {transcript.error}")

    text = (transcript.text or "").strip()
    detected = getattr(transcript, "language_code", None) or lang
    api_duration = getattr(transcript, "audio_duration", None)
    file_duration = round(float(api_duration), 1) if api_duration else audio_duration_seconds(audio_path)

    words = getattr(transcript, "words", None) or []
    active = _active_from_words(words) or file_duration
    shim = TranscribeInfo(language=detected, duration=api_duration or file_duration)
    return TranscribeResult(text, shim, file_duration, active)
