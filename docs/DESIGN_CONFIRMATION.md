# Design Confirmation

Open design questions that need your sign-off. Each item lists the recommendation, the alternatives, and what it blocks. Once you confirm an item, it moves to [decisions/](decisions) and stops being negotiable.

**How to use this file:** replace `[ ]` with `[x]` next to the option you want, or write your answer under the item. Anything left unconfirmed stays blocked.

**Legend for "Blocks":** the earliest sub-phase in [PLAN.md](PLAN.md) that cannot start without this answer.

---

## Confirmed already

These came out of conversation and are locked. Listed here so you can see them in one place; detail lives in [decisions/](decisions).

| # | Decision | Record |
|---|---|---|
| 1 | Hosting: white-glove, trust model C, 14-day retention, no permanent media vault | [0001](decisions/0001-hosting-white-glove-short-retention.md) |
| 2 | Monorepo layout: `apps/{api,web,worker}` + `packages/callqa` | [0002](decisions/0002-monorepo-layout.md) |
| 3 | Keep and refactor the Python engine; do not rewrite | [0003](decisions/0003-keep-python-engine.md) |
| 4 | Product is vertical-neutral; healthcare becomes one rubric pack | [0004](decisions/0004-vertical-neutral-rubric-packs.md) |
| 5 | Web is the primary report surface; Excel becomes an export | [0005](decisions/0005-web-primary-excel-export.md) |
| 6 | Project skills committed to the repo for cloud agents | [0006](decisions/0006-repo-skills-for-cloud-agents.md) |
| 7 | Intake = URL+ZIP; second rubric = generic; Phase 1 UI = API+shell | [0007](decisions/0007-phase0-intake-rubric-ui.md) |

**Also deferred (not blocking Phase 0–1):** C4 legacy 7 workbooks — decide with output work later.

---

## C1 — Database for Phase 1

**Blocks:** 1.1 (project and call model)

Recommendation: **SQLite via SQLAlchemy 2.x, written Postgres-compatible.** White-glove runs on a laptop should not require a database server, and the migration to Postgres is a connection-string change if we avoid SQLite-only constructs.

- [ ] SQLite now, Postgres-ready (recommended)
- [ ] Postgres from day one (adds Docker/service dependency to every run)
- [ ] Stay on JSON files, no database yet (keeps resume logic as-is, blocks web queries)

Consequence of the recommendation: `JSONB`-style columns become `JSON`; we avoid Postgres-specific indexing until Phase 4.

---

## C2 — Job execution model for Phase 1

**Blocks:** 1.4 (job runner)

Recommendation: **in-process background tasks with a durable job table**, upgrading to ARQ + Redis only when a real engagement needs parallel projects. Redis for a single operator is infrastructure without a customer.

- [ ] In-process worker + job table (recommended)
- [ ] ARQ + Redis now
- [ ] Celery + Redis now
- [ ] Keep shell-script batching, API only reads results

The engine already threads within a batch (`transcription_workers`, `analysis_workers`), so per-call parallelism exists regardless of this choice.

---

## C3 — Typed settings rollout order

**Blocks:** 0.4 (typed settings)

Recommendation: **incremental, ASR gate first.** Converting all 55 config keys at once touches every module and every test in one change.

- [ ] Incremental: `AsrGateSettings` → `CascadeSettings` → `RubricSpec` → `SelectionSettings` (recommended)
- [ ] One big conversion, single PR
- [ ] Leave `cfg: dict` alone; only new code uses typed settings

If you pick the third option, D1 in [PLAN.md](PLAN.md) stays a permanent tax and I will record it as a rejected-with-reason ADR rather than leaving it as an open item.

---

## C4 — Fate of `excel_legacy.py`

**Blocks:** 0.6 (prune dead paths)

[reports/excel_legacy.py](../packages/callqa/callqa/reports/excel_legacy.py) is 863 lines producing the older 7-workbook KIMS report set, reachable only when `report_template != "templates_v1"`.

- [ ] Delete it (recommended — deletion test says complexity vanishes)
- [ ] Move to `legacy/` unversioned, keep for reference
- [ ] Keep it wired; some engagement still needs those 7 books

I need to know whether any live or imminent engagement expects `KPI_SUMMARY`, `APPOINTMENT_CONV`, or `SURGICAL_PROCEDURES` before deleting.

---

## C5 — First non-healthcare rubric pack

**Blocks:** 0.5 (rubric packs), and Phase 1 exit criteria

We need a second pack to make the rubric seam real rather than hypothetical. Which vertical is your realistic second customer?

- [ ] Generic contact center (support/service, safest default)
- [ ] Inbound sales / lead qualification
- [ ] Collections
- [ ] Blank rubric the customer fills in during onboarding
- [ ] Other: ______

This choice sets the KPI names, escalation policy, and training module list for `templates/generic.yaml`.

---

## C6 — Recording intake shape

**Blocks:** 1.3 (ingestion refactor), 2.3 (upload wizard)

Today the engine downloads MP3s from `Recording URL` in the CDR. Small BPOs may not have URL-addressable recordings.

- [ ] Support both: CDR with recording URLs **and** direct file/ZIP upload (recommended)
- [ ] URL-only, as today
- [ ] Upload-only, drop URL fetching

"Both" means `CdrSource` and `RecordingFetcher` need a local-file adapter alongside the HTTP one — two adapters, so the seam is justified.

---

## C7 — Audio playback in Phase 2

**Blocks:** 2.6 (call detail)

Reviewing a disputed score is much easier with the audio, but streaming customer audio through a web app cuts against the locked short-retention posture.

- [ ] Transcript and scores only for MVP (recommended, matches retention posture)
- [ ] Local-only playback while media is still inside the retention window
- [ ] Full playback, treat audio as a first-class product asset (requires revisiting [0001](decisions/0001-hosting-white-glove-short-retention.md))

---

## C8 — Web styling approach

**Blocks:** 2.1 (design system)

I deliberately did not pick this in [PLAN.md](PLAN.md) because your `design/` assets should decide it.

- [ ] Tailwind, if the designs are utility/token friendly
- [ ] CSS modules, if the designs are bespoke and component-heavy
- [ ] Component library (shadcn/ui or similar) as the base, restyled to the designs
- [ ] Decide after I see `design/` (recommended)

---

## C9 — Who logs in during Phase 2

**Blocks:** 2.2 (app shell), and the shape of every endpoint

Under the locked white-glove model, the operator is you. But if a QA head is to see reports in a browser, someone outside your machine needs access.

- [ ] Operator-only, runs locally, no auth in Phase 2 (recommended for MVP)
- [ ] Single shared password per engagement (read-only link for the QA head)
- [ ] Real accounts now (pulls Phase 4 auth work forward)

This is the question most likely to change the Phase 2 endpoint design, so I would like it answered before 2.2.

---

## C10 — Naming and domain glossary

**Blocks:** nothing yet, but cheap to settle

The engine says `stem`, `cohort`, `pilot_agents`, and `bucket`. The product says project, call, agent, and duration band. Mixed vocabulary will leak into API field names and UI copy.

- [ ] Adopt product vocabulary everywhere, keep engine terms internal (recommended)
- [ ] Keep engine terms in the API too
- [ ] Write a `CONTEXT.md` glossary first, then decide

If you pick the first option I will create `CONTEXT.md` as the glossary and use it in every later plan.

---

## Answer summary

Fill this in and I will convert each line into a locked decision file.

| Item | Your answer |
|---|---|
| C1 database | |
| C2 job model | |
| C3 settings rollout | |
| C4 excel_legacy | |
| C5 second rubric | |
| C6 intake shape | |
| C7 audio playback | |
| C8 styling | |
| C9 auth in Phase 2 | |
| C10 vocabulary | |
