"""Provider registry — ASR and LLM adapters behind one lookup."""

from __future__ import annotations

from typing import Callable

from callqa.adapters import assemblyai, groq, stub, whisper

ASR_PROVIDERS: dict[str, Callable] = {
    "assemblyai": assemblyai.transcribe,
    "groq": groq.transcribe,
    "faster-whisper": whisper.transcribe,
    "stub-fail": stub.transcribe,
}

LLM_PROVIDERS = {
    "anthropic_claude": "anthropic",
    "anthropic": "anthropic",
}


def list_asr_providers() -> list[str]:
    return list(ASR_PROVIDERS.keys())


def get_asr_provider(name: str) -> Callable:
    key = (name or "").strip().lower()
    if key not in ASR_PROVIDERS:
        raise KeyError(f"unknown ASR provider: {name}")
    return ASR_PROVIDERS[key]


def resolve_llm_provider(name: str | None = None) -> str:
    key = (name or "anthropic_claude").strip().lower()
    return LLM_PROVIDERS.get(key, "anthropic")
