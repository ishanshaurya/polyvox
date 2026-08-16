"""Disposition → call outcome mapping (rules from config / rubric pack)."""

from __future__ import annotations

# Default rules used when config omits disposition_rules (healthcare-compatible).
_DEFAULT_RULES: list[tuple[tuple[str, ...], str]] = [
    (("Appointment_Booked", "Multiple_Appointments", "Resolved", "Completed", "Closed"), "Resolved"),
    (("Rescheduled", "Details_Shared", "Followup", "Follow-up", "Callback", "Pending"), "Follow-up Required"),
    (("Dropped", "Disconnected", "No_Response", "No Answer"), "Unresolved"),
    (("NotQualified", "No_Medical_Assistance", "Wrong_Number", "Spam"), "Wrong Number"),
]


def _rules_from_cfg(cfg: dict | None) -> list[tuple[tuple[str, ...], str]]:
    raw = (cfg or {}).get("disposition_rules")
    if not raw:
        return _DEFAULT_RULES
    out: list[tuple[tuple[str, ...], str]] = []
    for item in raw:
        needles = item.get("needles") or []
        outcome = item.get("outcome") or "Follow-up Required"
        if needles:
            out.append((tuple(str(n) for n in needles), str(outcome)))
    return out or _DEFAULT_RULES


def disposition_to_outcome(disposition: str, cfg: dict | None = None) -> str:
    """Map a CSV Disposition string to a Call Outcome label."""
    if not disposition:
        return "Follow-up Required"
    for needles, outcome in _rules_from_cfg(cfg):
        if any(n in disposition for n in needles):
            return outcome
    return "Follow-up Required"
