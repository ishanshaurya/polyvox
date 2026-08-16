"""Artifact storage seam — local workspace today, object storage later."""

from __future__ import annotations

import json
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ArtifactStore(ABC):
    """Interface for call artifacts. Paths stay inside the adapter."""

    @abstractmethod
    def audio_path(self, stem: str) -> Path: ...

    @abstractmethod
    def put_audio(self, stem: str, source: Path | bytes) -> Path: ...

    @abstractmethod
    def write_transcript(self, stem: str, text: str) -> Path: ...

    @abstractmethod
    def read_transcript(self, stem: str) -> str | None: ...

    @abstractmethod
    def write_analysis(self, stem: str, payload: dict[str, Any]) -> Path: ...

    @abstractmethod
    def read_analysis(self, stem: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def write_metadata(self, stem: str, payload: dict[str, Any]) -> Path: ...

    @abstractmethod
    def read_metadata(self, stem: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def reports_dir(self) -> Path: ...

    @abstractmethod
    def as_pipeline_cfg(self, base_cfg: dict) -> dict:
        """Return cfg copy with recordings_folder / output_folder set for legacy jobs."""


class LocalArtifactStore(ArtifactStore):
    """Per-engagement local folders (white-glove retention model)."""

    def __init__(self, workspace: Path | str):
        self.root = Path(workspace).resolve()
        self.recordings = self.root / "recordings"
        self.outputs = self.root / "outputs"
        for d in (
            self.recordings,
            self.outputs / "transcripts",
            self.outputs / "analysis",
            self.outputs / "metadata",
            self.outputs / "manifests",
            self.outputs / "reports",
            self.root / "inbox",
        ):
            d.mkdir(parents=True, exist_ok=True)

    def audio_path(self, stem: str) -> Path:
        return self.recordings / f"{stem}.mp3"

    def put_audio(self, stem: str, source: Path | bytes) -> Path:
        dest = self.audio_path(stem)
        if isinstance(source, bytes):
            dest.write_bytes(source)
        else:
            shutil.copy2(source, dest)
        return dest

    def write_transcript(self, stem: str, text: str) -> Path:
        path = self.outputs / "transcripts" / f"{stem}.txt"
        path.write_text(text, encoding="utf-8")
        return path

    def read_transcript(self, stem: str) -> str | None:
        path = self.outputs / "transcripts" / f"{stem}.txt"
        return path.read_text(encoding="utf-8") if path.exists() else None

    def write_analysis(self, stem: str, payload: dict[str, Any]) -> Path:
        path = self.outputs / "analysis" / f"{stem}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def read_analysis(self, stem: str) -> dict[str, Any] | None:
        path = self.outputs / "analysis" / f"{stem}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write_metadata(self, stem: str, payload: dict[str, Any]) -> Path:
        path = self.outputs / "metadata" / f"{stem}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def read_metadata(self, stem: str) -> dict[str, Any] | None:
        path = self.outputs / "metadata" / f"{stem}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def reports_dir(self) -> Path:
        return self.outputs / "reports"

    def as_pipeline_cfg(self, base_cfg: dict) -> dict:
        cfg = dict(base_cfg)
        cfg["recordings_folder"] = str(self.recordings)
        cfg["output_folder"] = str(self.outputs)
        return cfg
