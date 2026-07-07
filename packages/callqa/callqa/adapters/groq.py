"""Groq whisper-large-v3-turbo adapter."""

from __future__ import annotations

import time
from pathlib import Path

from callqa.config.loader import ensure_groq_api_key
from callqa.transcription.types import (
    TranscribeInfo,
    TranscribeResult,
    active_seconds_from_segments,
    audio_duration_seconds,
)


def groq_timeout_seconds(audio_secs: float | None) -> float:
    """Duration-scaled Groq timeout: min(600, max(60, audio_secs*0.5+30))."""
    secs = float(audio_secs) if audio_secs and audio_secs > 0 else 120.0
    return min(600.0, max(60.0, secs * 0.5 + 30.0))


def groq_transport_retries(cfg: dict) -> int:
    return int(cfg.get("groq_max_retries", 2))


def groq_max_backoff(cfg: dict) -> float:
    return float(cfg.get("groq_max_backoff_seconds", 8))


def groq_create(client, cfg: dict, *, timeout: float | None = None, **kwargs):
    max_retries = groq_transport_retries(cfg)
    max_backoff = groq_max_backoff(cfg)
    call_client = client.with_options(timeout=timeout) if timeout is not None else client
    for attempt in range(max_retries + 1):
        try:
            return call_client.audio.transcriptions.create(**kwargs)
        except Exception as exc:
            err = str(exc)
            retryable = (
                "429" in err
                or "502" in err
                or "503" in err
                or "rate" in err.lower()
                or "timed out" in err.lower()
                or "service_unavailable" in err.lower()
                or type(exc).__name__ in ("APITimeoutError", "ReadTimeout", "InternalServerError")
            )
            if retryable and attempt < max_retries:
                wait = min(max_backoff, 2 ** attempt)
                print(
                    f"   Groq retry {attempt + 1}/{max_retries} in {wait}s "
                    f"({type(exc).__name__})"
                )
                time.sleep(wait)
                continue
            raise


def load_groq_client(cfg: dict, *, model_override: str | None = None):
    try:
        from groq import Groq
    except ImportError:
        raise RuntimeError("groq not installed — pip install groq")

    api_key = ensure_groq_api_key(cfg)
    model = model_override or cfg.get("groq_whisper_model", "whisper-large-v3-turbo")
    return Groq(api_key=api_key, timeout=600.0, max_retries=0), model


def transcribe(
    audio_path: Path,
    *,
    language_hint: str | None,
    prompt: str | None,
    cfg: dict,
    client=None,
    model: str | None = None,
) -> TranscribeResult:
    if client is None or model is None:
        client, model = load_groq_client(cfg, model_override=model)

    audio_secs = audio_duration_seconds(audio_path)
    timeout = groq_timeout_seconds(audio_secs)
    create_kw: dict = {
        "file": (audio_path.name, open(audio_path, "rb")),
        "model": model,
        "response_format": "verbose_json",
        "temperature": 0.0,
        "timestamp_granularities": ["segment"],
    }
    if language_hint:
        create_kw["language"] = language_hint
    if prompt:
        create_kw["prompt"] = prompt

    try:
        result = groq_create(client, cfg, timeout=timeout, **create_kw)
    finally:
        create_kw["file"][1].close()

    transcript_text = (result.text or "").strip()
    detected_lang = getattr(result, "language", None) or language_hint
    segments = getattr(result, "segments", None) or []
    api_duration = getattr(result, "duration", None)
    file_duration = round(api_duration, 1) if api_duration else audio_duration_seconds(audio_path)
    active = active_seconds_from_segments(segments) or file_duration
    shim = TranscribeInfo(language=detected_lang, duration=api_duration or file_duration)
    return TranscribeResult(transcript_text, shim, file_duration, active)
