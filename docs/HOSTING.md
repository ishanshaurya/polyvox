# Hosting decision (locked)

**Date locked:** 2026-08-16  
**Applies to:** Phase 0–1 product framework (pre–self-serve SaaS)

## Decision

| Topic | Choice |
|---|---|
| Buyer | Small BPO / office QA heads (any geography) |
| Trust model | **C** — Process under NDA/DPA; **no long-term multi-tenant media vault** |
| Ops model | **White-glove** — we run the pipeline for the customer |
| Customer delivery | ZIP / USB / SFTP dump; we process and **delete within 7–14 days** |
| Third-party AI | OK to disclose: AssemblyAI / Groq / Claude process audio or transcripts |
| Self-serve web upload SaaS | **Deferred** — plan later |
| Infra budget | Near-zero excluding API usage |
| Storage | Local disk (or ephemeral path) per engagement — **not** a permanent product S3 archive |

## What we are *not* building yet

- Multi-tenant cloud storage of customer recordings
- Self-serve “upload and leave” SaaS
- Per-customer full stack deploys (N Kubernetes apps)
- On-prem-only / air-gapped LLM (unless a later enterprise tier)

## How the framework should behave

1. **One toolkit** (this monorepo): API + worker + web shell + `packages/callqa` engine.
2. **Per engagement = workspace folder** (or DB `project` with `retention_days`), not a forever vault.
3. API/web exist so we can productize UX early, while operators still run white-glove jobs.
4. Retention: hard delete audio/transcripts after `retention_days` (default 14).

## Disclosure line for pilots

> Call audio/transcripts are processed by speech and LLM providers (e.g. AssemblyAI, Groq, Anthropic) to produce QA scores. We do not keep a long-term archive of your recordings; pilot data is deleted within 14 days of delivery unless a written agreement says otherwise.
