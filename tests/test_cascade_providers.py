"""Transcription cascade resolution — default, per-language, refine override."""

import _bootstrap  # noqa: F401

from callqa.transcription.engine import cascade_providers


def test_default_cascade():
    cfg = {"transcription_cascade": ["assemblyai", "groq"]}
    assert cascade_providers(cfg) == ["assemblyai", "groq"]


def test_language_override():
    cfg = {
        "transcription_cascade": ["assemblyai", "groq"],
        "transcription_cascade_by_language": {
            "te": ["groq", "assemblyai"],
        },
    }
    assert cascade_providers(cfg, language_hint="te") == ["groq", "assemblyai"]
    assert cascade_providers(cfg, language_hint="en") == ["assemblyai", "groq"]


def test_cascade_from_refine_still_reaches_faster_whisper():
    cfg = {"transcription_cascade": ["assemblyai", "groq"]}
    assert cascade_providers(cfg, cascade_from="faster-whisper") == ["faster-whisper"]


def test_cascade_from_ignores_language_override():
    cfg = {
        "transcription_cascade": ["assemblyai", "groq", "faster-whisper"],
        "transcription_cascade_by_language": {"te": ["groq"]},
    }
    assert cascade_providers(cfg, cascade_from="groq", language_hint="te") == [
        "groq",
        "faster-whisper",
    ]


if __name__ == "__main__":
    test_default_cascade()
    test_language_override()
    test_cascade_from_refine_still_reaches_faster_whisper()
    test_cascade_from_ignores_language_override()
    print("test_cascade_providers: OK")
