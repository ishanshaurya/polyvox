# 0004 — Vertical-neutral product; healthcare is one rubric pack

**Status:** Locked  
**Date:** 2026-08-16

## Context

The pipeline was built for a hospital call center, and healthcare assumptions are spread through Python rather than confined to configuration:

- Healthcare prompt copy, escalation policy, and "patient" vocabulary in [analysis/plugins/generic.py](../../packages/callqa/callqa/analysis/plugins/generic.py)
- `profiles.get_profile()` always returning that single profile, so the seam is hypothetical
- Vendor-specific disposition strings in [state/disposition.py](../../packages/callqa/callqa/state/disposition.py) (`Appointment_Booked`, `No_Medical_Assistance`)
- `hospital` as a first-class metadata field, defaulting to `"Rainbow"` in [state/metadata.py](../../packages/callqa/callqa/state/metadata.py)

The stated product goal is to sell to QA heads generally, not to hospitals specifically.

## Decision

1. **No vertical is privileged in code.** Healthcare becomes `templates/healthcare.yaml`, one pack among several.
2. **A rubric pack is data**, carrying KPIs and weights, escalation policy, training module list, tone and vocabulary, and disposition-to-outcome rules.
3. **One prompt builder consumes packs.** The per-profile Python plugin pattern collapses into a pack registry.
4. **A second pack ships in Phase 0.** One adapter is a hypothetical seam; two make it real. Without a second pack we cannot claim the product is vertical-neutral.
5. **Customer-specific strings never gate behaviour.** No `if "royalbhrn" in stem` style logic in the product path.

## Consequences

- `hospital` generalizes to something like `site` or `location` in the product vocabulary, pending C10 in [../DESIGN_CONFIRMATION.md](../DESIGN_CONFIRMATION.md).
- Legacy filename parsing for the hospital engagement moves behind a compatibility adapter rather than living in the default resolution path.
- Onboarding a customer becomes a rubric conversation plus a column mapping, not a code fork.
- Phase 3's rubric builder UI has something coherent to edit, because the rubric is already data.

## Reopen when

We decide to become a healthcare-only vertical product, which would make packs unnecessary indirection.
