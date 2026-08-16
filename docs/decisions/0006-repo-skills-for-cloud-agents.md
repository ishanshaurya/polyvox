# 0006 — Commit agent skills to the repo

**Status:** Locked  
**Date:** 2026-08-16

## Context

Cursor Cloud Agents run on an isolated VM that clones the repository. Skills installed on a developer's machine under `~/.cursor/skills/` or `~/.agents/skills/` are user-level and do not travel to that VM, so invoking them in a cloud session fails. There is no documented mechanism to sync personal or team skills into a cloud run.

This surfaced when `/caveman`, `/handsoff`, and `/improvecodebase` were unavailable mid-session despite being installed locally.

## Decision

Skills the team relies on are **committed to the repository** under `.cursor/skills/`, so they arrive with the checkout:

| Skill | Invoked as | Upstream |
|---|---|---|
| caveman | `/caveman` | JuliusBrussee/caveman (MIT) |
| grill-me, grilling | `/grill-me` | mattpocock/skills (MIT) |
| handoff, handsoff | `/handoff`, `/handsoff` | mattpocock/skills (MIT) |
| improve-codebase-architecture, improvecodebase | `/improve-codebase-architecture` | mattpocock/skills (MIT) |
| codebase-design | used by the architecture skill | mattpocock/skills (MIT) |

`handsoff` and `improvecodebase` are thin aliases matching how the commands are actually typed.

## Consequences

- `.gitignore` needed narrowing: a blanket `.cursor/` rule excluded the skills directory.
- Skills added mid-session are not retroactively discovered. A cloud agent picks them up when it starts on a revision containing them; within an existing session the agent must read the `SKILL.md` directly.
- Upstream licences are MIT; attribution stays in [.cursor/skills/README.md](../../.cursor/skills/README.md).
- Vendored copies drift from upstream. Refreshing is a deliberate act, not automatic.

## Reopen when

Cursor ships an official mechanism to provision user or team skills into cloud runs, at which point vendoring becomes redundant.
