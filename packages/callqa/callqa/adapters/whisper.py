"""Local faster-whisper large-v3 adapter."""

from __future__ import annotations

from pathlib import Path

from callqa.transcription.types import (
    TranscribeInfo,
    TranscribeResult,
    active_seconds_from_segments,
    audio_duration_seconds,
)


def load_whisper_model(cfg: dict):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("faster-whisper not installed — pip install faster-whisper")

    device = "cpu"
    compute_type = "int8"
    try:
        import torch
        if torch.cuda.is_available():
            device = "cuda"
            compute_type = "float16"
    except ImportError:
        pass

    model_name = cfg.get("whisper_model", "large-v3")
    print(f"  Loading faster-whisper {model_name} on {device}...")
    return WhisperModel(model_name, device=device, compute_type=compute_type)


def transcribe(
    audio_path: Path,
    *,
    language_hint: str | None,
    prompt: str | None,
    cfg: dict,
    model=None,
    beam_size: int | None = None,
    is_retry: bool = False,
) -> TranscribeResult:
    if model is None:
        model = load_whisper_model(cfg)

    beam = beam_size if beam_size is not None else int(cfg.get("whisper_beam_size", 5))
    transcribe_kw: dict = {"vad_filter": True, "beam_size": beam}
    if language_hint:
        transcribe_kw["language"] = language_hint
    if prompt:
        transcribe_kw["initial_prompt"] = prompt
    if is_retry:
        transcribe_kw["condition_on_previous_text"] = False
        vad_params = cfg.get("whisper_vad_parameters_retry")
        if vad_params:
            transcribe_kw["vad_parameters"] = vad_params

    segments, info = model.transcribe(str(audio_path), **transcribe_kw)
    seg_list = list(segments)
    text_parts = [seg.text.strip() for seg in seg_list if seg.text.strip()]
    transcript_text = " ".join(text_parts).strip()
    file_duration = round(info.duration, 1) if info.duration else audio_duration_seconds(audio_path)
    active = None
    if getattr(info, "duration_after_vad", None):
        active = round(float(info.duration_after_vad), 1)
    if not active:
        active = active_seconds_from_segments(seg_list)
    shim = TranscribeInfo(language=info.language, duration=info.duration)
    return TranscribeResult(transcript_text, shim, file_duration, active)
