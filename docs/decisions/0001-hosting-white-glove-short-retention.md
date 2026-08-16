# 0001 — Hosting: white-glove with short retention

**Status:** Locked  
**Date:** 2026-08-16  
**Supersedes:** nothing

## Context

The target buyer is a QA head at a small BPO or office, anywhere geographically. When asked whether customer call recordings could live in our cloud, the answer was "no way" — clarified as **trust model C**: processing under NDA is acceptable, a permanent multi-tenant media vault is not.

Two facts constrain the design:

1. A self-serve SaaS that stores recordings contradicts the buyer's stated objection, and our own free-tier S3 would still be "our servers."
2. The pipeline already sends audio or transcripts to AssemblyAI, Groq, and Anthropic. "No cloud at all" would mean local Whisper plus a local LLM, which costs quality and hardware.

Infrastructure budget is near zero excluding API usage.

## Decision

1. **Operating model is white-glove.** We run the pipeline for the customer. Self-serve upload SaaS is deferred, not cancelled.
2. **Trust model C.** Process under NDA or DPA; no long-term multi-tenant archive of customer media.
3. **Retention is 14 days by default**, configurable per engagement between 1 and 90 days. Media is hard-deleted when the window elapses; derived scores and reports may survive.
4. **Third-party AI processing is disclosed**, not hidden. The pilot disclosure line lives in [../HOSTING.md](../HOSTING.md).
5. **Customer media lives in a per-engagement workspace** on operator-controlled local storage, never in a shared permanent bucket.
6. **Intake is a dump**, delivered as ZIP, USB, or SFTP, rather than a persistent sync.

## Consequences

- Phase 1 builds a project-scoped API and job runner, not tenant-scoped cloud storage.
- No object storage, no Redis, no managed Postgres is required to ship Phase 1.
- The `ArtifactStore` seam must support a local adapter first; a remote adapter is speculative until this decision is revisited.
- Retention enforcement is a product feature, not an afterthought: every project carries a purge deadline.
- Deleting media must not delete scores, otherwise reports evaporate mid-engagement.
- Auth can stay minimal through Phase 2 because there are no external tenants yet.

## Reopen when

- A buyer signs who explicitly wants hosted self-serve upload, or
- An enterprise buyer requires their own VPC deployment (Phase 6), or
- Retention longer than 90 days is contractually required.

Any of these needs a new decision file superseding this one, plus a revision of the disclosure line.
