# Architecture — product framework (Phase 0)

## Layout

```
polyvox/
├── apps/
│   ├── api/       # FastAPI — product HTTP surface
│   ├── web/       # React (Vite) — UI shell (designs → design/)
│   ├── worker/    # Job runner stub (wraps packages/callqa)
│   └── cli/       # Existing CLI (legacy entry)
├── packages/callqa/   # Existing pipeline engine
├── design/            # Drop UI designs/assets here
├── templates/         # Rubric YAML packs
└── docs/HOSTING.md    # Locked hosting / retention decision
```

## Runtime model (now)

White-glove + short retention (see [HOSTING.md](HOSTING.md)):

1. Operator creates a **project** (engagement) via API or CLI.
2. Customer dump lands in a **project workspace** on local disk.
3. Worker runs `callqa` pipeline steps against that workspace.
4. Web UI (when wired) reads scores from the API — Excel export remains optional.
5. After `retention_days`, workspace media is deleted.

## Next build slices (not all at once)

1. API: projects, retention, health (this scaffold)
2. Worker: call existing `1_transcribe` / `2_analyze` / `3_report` for a project path
3. Web: pages from `design/` against API
4. Later: auth, Postgres, self-serve upload
