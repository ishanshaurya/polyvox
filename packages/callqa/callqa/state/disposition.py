"""CSV Disposition → report Call Outcome mapping (pilot cohort)."""

from __future__ import annotations

# Order matters: first substring match wins.
_DISPOSITION_RULES: list[tuple[tuple[str, ...], str]] = [
    (("Appointment_Booked", "Multiple_Appointments"), "Resolved"),
    (("Rescheduled", "Details_Shared", "Followup"), "Follow-up Required"),
    (("Dropped", "Disconnected", "No_Response"), "Unresolved"),
    (("NotQualified", "No_Medical_Assistance"), "Wrong Number"),
]


def disposition_to_outcome(disposition: str) -> str:
    """Map a CSV Disposition string to the template Call Outcome enum."""
    if not disposition:
        return "Follow-up Required"
    for needles, outcome in _DISPOSITION_RULES:
        if any(n in disposition for n in needles):
            return outcome
    return "Follow-up Required"
