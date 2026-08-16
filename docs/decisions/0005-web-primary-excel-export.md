# 0005 — Web is the primary report surface; Excel is an export

**Status:** Locked  
**Date:** 2026-08-16

## Context

The pipeline's deliverable is four timestamped Excel workbooks written by [reports/templates_v1.py](../../packages/callqa/callqa/reports/templates_v1.py): call log, escalations, patient complaints, and agent evaluations. Excel earned its place — QA teams share workbooks — but it constrains the product:

- No progress visibility while a batch runs
- No drill-down from a score into the transcript that produced it
- No retry affordance for ASR failures without an operator running [refine_analysis.py](../../refine_analysis.py)
- Reports are regenerated wholesale; the folder is wiped before each write

The stated goal is reports available on the web after documents are uploaded.

## Decision

1. **The web app is the primary reporting surface** from Phase 2 onward.
2. **Excel becomes an export endpoint**, generated on demand from the same records the web UI reads.
3. **No feature may be Excel-only** from Phase 1 onward. Anything a workbook can show, the API must expose.
4. **One aggregation module feeds both.** The duplicate `_merge_records` in [reports/templates_v1.py](../../packages/callqa/callqa/reports/templates_v1.py) and [reports/aggregator.py](../../packages/callqa/callqa/reports/aggregator.py) collapses into one, and the API consumes it too.
5. **"Not scored" stays visually distinct from "scored badly."** The ASR-fail distinction the workbooks make must survive into the UI.

## Consequences

- Analysis records become the product's source of truth, and the Excel writer becomes one consumer among several.
- Report generation stops being a destructive whole-folder rewrite and becomes a query plus a render.
- The email-attachment delivery path in [run_all.py](../../run_all.py) is legacy; notifications in Phase 4 will link to the web instead of attaching workbooks. That path also still references the wrong branding and report count.
- Agent rollup rules, including the minimum-calls threshold before a rating is shown, must be expressed once and shared by both surfaces.

## Reopen when

A buyer segment emerges that will not use a web tool at all, making the workbook the product again.
