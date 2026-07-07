"""TranscriptionEngine — cascade orchestrator (AssemblyAI → Groq → faster-whisper)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from callqa.adapters import assemblyai, groq, stub, whisper

from . import asr_gate
from . import normalize
from .types import (
    TranscribeInfo,
    TranscribeResult,
    active_seconds_from_segments,
    audio_duration_seconds,
    norm_lang,
)

_INDIC_HINTS = frozenset({"te", "hi", "ta"})
_HIGH_LATIN_RATIO = 0.70


@dataclass
class CascadeOutcome:
    text: str
    result: TranscribeResult
    gate: dict
    lang_used: str | None
    provider: str
    asr_attempts: list[dict]
    retried: bool


def normalize_transcript(text: str, cfg: dict) -> str:
    cleaned = normalize.strip_prompt_echo(text, cfg)
    cleaned = normalize.dedupe_hold_phrases(cleaned)
    if cfg.get("asr_dedupe_ngrams", True):
        cleaned = normalize.dedupe_repeated_ngrams(cleaned)
    return cleaned


def gate_evaluate(
    text: str,
    file_duration: float | None,
    active_seconds: float | None,
    cfg: dict,
    *,
    language: str | None,
) -> dict:
    return asr_gate.evaluate(
        text,
        file_duration,
        cfg,
        language=language,
        speech_duration_seconds=active_seconds,
    )


def gate_rank(gate: dict) -> tuple:
    m = gate["metrics"]
    return (
        1 if gate["pass"] else 0,
        m.get("word_count", 0),
        -m.get("repetition_score", 1.0),
        -m.get("gibberish_score", 1.0),
    )


def attempt_acceptable(gate: dict, lang_hint: str | None) -> bool:
    """True when cascade can stop (passed gate + no high-latin on indic hint)."""
    if not gate["pass"]:
        return False
    hint = norm_lang(lang_hint)
    if hint in _INDIC_HINTS and gate["metrics"].get("latin_ratio", 0) > _HIGH_LATIN_RATIO:
        return False
    return True


def prompt_for_language(cfg: dict, language: str | None, *, fallback: str | None) -> str | None:
    lang_prompts = cfg.get("whisper_language_prompts") or {}
    if language and language in lang_prompts:
        return lang_prompts[language]
    return fallback


_DEFAULT_CASCADE = ["assemblyai", "groq", "faster-whisper"]


def cascade_providers(
    cfg: dict,
    *,
    cascade_from: str | None = None,
    language_hint: str | None = None,
) -> list[str]:
    if cascade_from:
        cascade = list(cfg.get("transcription_cascade") or _DEFAULT_CASCADE)
    else:
        by_lang = cfg.get("transcription_cascade_by_language") or {}
        lang = norm_lang(language_hint)
        if lang and lang in by_lang:
            cascade = list(by_lang[lang])
        else:
            cascade = list(cfg.get("transcription_cascade") or _DEFAULT_CASCADE)
    if cascade_from:
        try:
            idx = cascade.index(cascade_from)
            cascade = cascade[idx:]
        except ValueError:
            cascade = [cascade_from]
    return cascade


class TranscriptionEngine:
    """Run one attempt per provider in cascade order; pick best gate-ranked result."""

    def __init__(
        self,
        cfg: dict,
        *,
        cascade_from: str | None = None,
        groq_model_override: str | None = None,
        whisper_model=None,
        groq_client=None,
        groq_model: str | None = None,
        whisper_lock=None,
    ):
        self.cfg = cfg
        self._cascade_from = cascade_from
        self.cascade = cascade_providers(cfg, cascade_from=cascade_from)
        self.initial_prompt = cfg.get("whisper_initial_prompt") or None
        self.groq_model_override = groq_model_override
        self._whisper_model = whisper_model
        self._groq_client = groq_client
        self._groq_model = groq_model
        self._whisper_lock = whisper_lock

    def _ensure_groq(self):
        if self._groq_client is None:
            self._groq_client, self._groq_model = groq.load_groq_client(
                self.cfg, model_override=self.groq_model_override
            )

    def _ensure_whisper(self):
        if self._whisper_model is None:
            self._whisper_model = whisper.load_whisper_model(self.cfg)

    def _run_provider(
        self,
        provider: str,
        audio_path: Path,
        *,
        language_hint: str | None,
        prompt: str | None,
    ) -> TranscribeResult:
        if provider == "groq":
            self._ensure_groq()
            return groq.transcribe(
                audio_path,
                language_hint=language_hint,
                prompt=prompt,
                cfg=self.cfg,
                client=self._groq_client,
                model=self._groq_model,
            )
        if provider == "faster-whisper":
            self._ensure_whisper()
            if self._whisper_lock:
                with self._whisper_lock:
                    return whisper.transcribe(
                        audio_path,
                        language_hint=language_hint,
                        prompt=prompt,
                        cfg=self.cfg,
                        model=self._whisper_model,
                    )
            return whisper.transcribe(
                audio_path,
                language_hint=language_hint,
                prompt=prompt,
                cfg=self.cfg,
                model=self._whisper_model,
            )
        if provider == "assemblyai":
            return assemblyai.transcribe(
                audio_path,
                language_hint=language_hint,
                prompt=prompt,
                cfg=self.cfg,
            )
        if provider == "stub-fail":
            return stub.transcribe(
                audio_path,
                language_hint=language_hint,
                prompt=prompt,
                cfg=self.cfg,
            )
        raise ValueError(f"unknown transcription provider: {provider}")

    def transcribe_call(
        self,
        audio_path: Path,
        *,
        language_hint: str | None,
    ) -> CascadeOutcome:
        cfg = self.cfg
        lang = norm_lang(language_hint)
        prompt = prompt_for_language(cfg, lang, fallback=self.initial_prompt)
        effective_cascade = cascade_providers(
            cfg,
            cascade_from=self._cascade_from,
            language_hint=language_hint,
        )
        best: tuple[str, TranscribeResult, dict, str, str] | None = None
        asr_attempts: list[dict] = []
        retried = False

        for idx, provider in enumerate(effective_cascade):
            if idx > 0:
                retried = True
                print(f"   cascade fallback: {provider}")
            try:
                attempt_result = self._run_provider(
                    provider,
                    audio_path,
                    language_hint=lang,
                    prompt=prompt,
                )
            except Exception as exc:
                print(f"   {provider} error: {type(exc).__name__}: {exc}")
                asr_attempts.append({
                    "provider": provider,
                    "lang": lang,
                    "pass": False,
                    "reasons": [f"transcribe_error:{type(exc).__name__}"],
                    "metrics": {},
                })
                continue

            attempt_text = normalize_transcript(attempt_result.text, cfg)
            attempt_gate = gate_evaluate(
                attempt_text,
                attempt_result.file_duration,
                attempt_result.active_seconds,
                cfg,
                language=lang,
            )
            asr_attempts.append({
                "provider": provider,
                "lang": lang,
                "pass": attempt_gate["pass"],
                "reasons": attempt_gate.get("reasons", []),
                "metrics": attempt_gate["metrics"],
            })

            if best is None or gate_rank(attempt_gate) > gate_rank(best[2]):
                best = (attempt_text, attempt_result, attempt_gate, lang, provider)

            if attempt_acceptable(attempt_gate, language_hint):
                break

            if idx == 0 and attempt_gate.get("reasons"):
                print(f"   ASR fail ({', '.join(attempt_gate['reasons'])})")

        if best is None:
            stub = self._run_provider(
                "stub-fail",
                audio_path,
                language_hint=lang,
                prompt=prompt,
            )
            gate = gate_evaluate("", None, None, cfg, language=lang)
            gate["pass"] = False
            gate.setdefault("reasons", []).append("asr_unavailable")
            asr_attempts.append({
                "provider": "stub-fail",
                "lang": lang,
                "pass": False,
                "reasons": gate["reasons"],
                "metrics": gate["metrics"],
            })
            return CascadeOutcome("", stub, gate, lang, "stub-fail", asr_attempts, retried)

        text, result, gate, lang_used, provider_used = best
        return CascadeOutcome(text, result, gate, lang_used, provider_used, asr_attempts, retried)
