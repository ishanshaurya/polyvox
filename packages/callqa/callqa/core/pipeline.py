"""High-level pipeline entrypoints for workers and the API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from callqa.core.types import AnalysisResult, ExportArtifact
from callqa.storage.artifacts import ArtifactStore, LocalArtifactStore


def store_from_workspace(workspace: Path | str) -> LocalArtifactStore:
    return LocalArtifactStore(workspace)


def run_transcribe(
    cfg: dict,
    store: ArtifactStore,
    *,
    batch: int,
    force: bool = False,
    stems: set[str] | None = None,
) -> int:
    from callqa.jobs import transcribe as transcribe_job

    pipeline_cfg = store.as_pipeline_cfg(cfg)
    return transcribe_job.transcribe_batch(
        pipeline_cfg, batch, force=force, stems=stems
    )


def run_analyze(
    cfg: dict,
    store: ArtifactStore,
    *,
    batch: int,
    force: bool = False,
    stems: set[str] | None = None,
) -> int:
    from callqa.jobs import analyze as analyze_job

    pipeline_cfg = store.as_pipeline_cfg(cfg)
    return analyze_job.analyze_batch(
        pipeline_cfg, batch, force=force, stems=stems
    )


def run_export(
    cfg: dict,
    store: ArtifactStore,
    *,
    batch: int | None = None,
    batch_only: bool = False,
) -> ExportArtifact:
    from callqa.jobs import report as report_job

    pipeline_cfg = store.as_pipeline_cfg(cfg)
    paths = report_job.generate(pipeline_cfg, batch=batch, batch_only=batch_only)
    return ExportArtifact(format="xlsx", paths=list(paths or []), label="templates_v1")


def load_call_analysis(store: ArtifactStore, stem: str) -> AnalysisResult | None:
    payload = store.read_analysis(stem)
    if not payload:
        return None
    score = payload.get("overall_score")
    try:
        overall = float(score) if score not in (None, "") else None
    except (TypeError, ValueError):
        overall = None
    return AnalysisResult(
        call_id=stem,
        payload=payload,
        unclear=bool(payload.get("unclear_recording")),
        overall_score=overall,
    )


def list_analyses(store: ArtifactStore) -> list[dict[str, Any]]:
    from callqa.reports.aggregator import load_all_analyses, merge_records

    cfg = store.as_pipeline_cfg({})
    return merge_records(cfg, load_all_analyses(cfg))
