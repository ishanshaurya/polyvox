# 0003 — Keep and refactor the Python engine

**Status:** Locked  
**Date:** 2026-08-16

## Context

Rebuilding as a product invites a rewrite. But the genuinely hard, validated work already exists in `packages/callqa`:

- A multi-provider ASR cascade with best-result ranking ([transcription/engine.py](../../packages/callqa/callqa/transcription/engine.py))
- A language-aware quality gate including the Indic latin-script failure mode ([transcription/asr_gate.py](../../packages/callqa/callqa/transcription/asr_gate.py))
- An escalation policy separated from score floors, so a low score is not an escalation ([analysis/plugins/generic.py](../../packages/callqa/callqa/analysis/plugins/generic.py))
- Stub analysis for failed ASR, so the product never invents KPI scores it cannot justify
- Resume-safe batching that survives rate limits

That behaviour represents the accumulated field knowledge from the hospital engagement. It is also the part a rewrite would silently lose.

## Decision

1. **The engine stays Python and stays in `packages/callqa`.** No rewrite in another language or framework.
2. **Refactor targets interfaces, not behaviour.** Typed settings and an artifact seam change how modules are called, not what the cascade or gate decides.
3. **The API and worker are thin callers.** Product logic must not accumulate in `apps/api`; it belongs behind the engine's pipeline interface.
4. **Deleting the ASR gate, cascade ranking, or ASR-fail stub requires its own decision file.** These are load-bearing.

## Consequences

- FastAPI is the natural API choice: same language, direct import of the engine, no serialization boundary between web layer and pipeline.
- Refactors must keep the existing test fixtures meaningful — [tests/test_asr_gate.py](../../tests/test_asr_gate.py) encodes real regression cases and is the safety net for D1 and D2 work.
- Any behaviour change to scoring needs to be visible: reports already distinguish "not scored" from "scored zero," and that distinction must survive.

## Reopen when

The engine becomes the bottleneck for a requirement it structurally cannot meet, for example real-time streaming analysis during a live call.
