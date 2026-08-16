# 0007 — Phase 0 open decisions: intake, second rubric, Phase 1 UI

**Status:** Locked  
**Date:** 2026-08-16  
**Supersedes:** open items C5, C6, and the Phase 0 tenancy question in the original rebuild plan

## Context

The original rebuild plan required locking tenancy, upload format, and the first non-Rainbow rubric before Phase 1. Hosting and tenancy were already settled in [0001](0001-hosting-white-glove-short-retention.md) (white-glove engagements, not multi-tenant SaaS media vault). Two remaining product questions blocked Phase 0.5 and Phase 1.3.

Legacy Excel workbooks (`excel_legacy.py`) stay deferred — output is last; see [../DESIGN_CONFIRMATION.md](../DESIGN_CONFIRMATION.md) C4.

## Decision

1. **Tenancy for Phase 0–2:** white-glove per-engagement projects under one operator toolkit (already [0001](0001-hosting-white-glove-short-retention.md)). No self-serve multi-tenant org vault yet.
2. **Recording intake:** support **both** CDR rows with recording URLs and direct file/ZIP upload into a project workspace.
3. **First non-healthcare rubric pack:** `generic` — generic contact-center / support QA (not sales or collections-specific).
4. **Phase 1 UI:** API + existing web shell is enough; full design-driven MVP is Phase 2 after `design/` assets land.
5. **Audio on web (Phase 2 default):** transcript and scores first; playback only while media remains inside the retention window, not as a permanent product asset.

## Consequences

- `templates/generic.yaml` ships in Phase 0.
- Ingestion grows a local-file recording adapter beside HTTP download.
- Phase 1 data model uses project-scoped tables; `organizations` may exist as a thin optional label for future SaaS, not as a media tenancy boundary.
- Object storage in the original plan maps to the local `ArtifactStore` adapter until hosting is reopened.

## Reopen when

A paying customer requires sales/collections KPIs as the default pack, or hosted self-serve upload is contractually required.
