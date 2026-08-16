"""Core pipeline types — no filesystem paths in public interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class CallRef:
    """Stable reference to one call inside a project workspace."""

    call_id: str
    stem: str
    agent_name: str = ""
    batch: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class TranscriptResult:
    call_id: str
    text: str
    asr_pass: bool
    provider: str = ""
    language: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    call_id: str
    payload: dict[str, Any]
    unclear: bool = False
    overall_score: float | None = None


@dataclass
class ExportArtifact:
    format: Literal["xlsx"]
    paths: list[str]
    label: str = ""
