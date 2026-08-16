# 0002 — Monorepo layout

**Status:** Locked  
**Date:** 2026-08-16

## Context

The repository was a flat batch pipeline: numbered root scripts, one `config.yaml`, and `packages/callqa` holding the real logic. Adding a web product needed somewhere for an API, a frontend, and a job runner without breaking the existing operator workflow.

## Decision

One repository, four applications, one engine package:

```
polyvox/
├── apps/
│   ├── api/       FastAPI product surface
│   ├── web/       React UI
│   ├── worker/    Pipeline job runner
│   └── cli/       Existing CLI entry
├── packages/callqa/   Pipeline engine
├── design/            UI design assets
├── templates/         Rubric packs
├── docs/              Plan, decisions, architecture
└── tests/
```

Supporting rules:

- `packages/callqa` stays importable standalone; apps depend on it, never the reverse.
- Root numbered scripts (`0_fetch_csv.py` … `3_report.py`) keep working during the transition so in-flight engagements are not disrupted.
- `design/` is the single source for UI assets; the web app implements them rather than inventing a parallel design system.

## Consequences

- The worker, not the API, is where long pipeline steps run — the API stays responsive.
- Root scripts are duplicated capability during transition; they get retired only after the worker covers their behaviour.
- `.gitignore` needed narrowing: a blanket `src/` rule was hiding `apps/web/src`, and `.cursor/` was hiding committed skills.

## Reopen when

The web app needs server-side rendering or a separate deploy cadence significant enough to justify splitting repositories.
