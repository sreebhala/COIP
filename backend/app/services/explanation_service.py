"""
Explanation Service — Post #1.5.

Deterministic, template-based only. No LLM. Converts an already-decided
result into a passenger/staff-readable explanation. Adds no new facts, per
the Audit and Explainability Guide's explanation rules:
  - Use deterministic templates.
  - Use only operational facts already present in the decision record.
  - Never mention diagnosis, severity, treatment, or clinical recommendation.
  - Never guarantee wait time.
  - Never expose unnecessary contact information.
  - Clearly state when human review is required.
"""
from typing import Any


def build_explanation(
    decision_category: str,
    schedule_output: Any,
    queue_output: Any,
    resource_output: Any,
    attendance_follow_up_output: Any,
) -> str:
    parts: list[str] = []

    if decision_category == "Confirm Slot":
        parts.append(
            f"The requested appointment slot is confirmed"
            f"{f' at {schedule_output.recommendation}' if schedule_output.recommendation else ''}."
        )
        if resource_output.recommendation:
            parts.append(f"Room {resource_output.recommendation} has been allocated.")
        parts.append(f"Current clinic queue status is {queue_output.classification.lower()}.")

    elif decision_category == "Await Confirmation":
        parts.append(
            "The requested slot is operationally available, but patient confirmation "
            "is required before the appointment can be finalized."
        )

    elif decision_category == "Suggest Alternative":
        if schedule_output.recommendation:
            parts.append(
                f"The exact requested time is not available. An alternative option "
                f"({schedule_output.recommendation}) is suggested instead."
            )
        else:
            parts.append("The exact requested time is not available. An alternative option is suggested.")

    elif decision_category == "Needs Review":
        parts.append(
            "This request requires human review because required operational "
            "information could not be fully confirmed by the system."
        )

    elif decision_category == "Reject":
        parts.append(
            "This request could not be processed as submitted. Please review the "
            "request details (date, location, or appointment type) and resubmit."
        )

    # Operational-only add-ons, never altering the decision itself.
    if attendance_follow_up_output.classification == "repeated_missed_appointments":
        parts.append(
            "Operational note: recent appointment history shows repeated missed "
            "visits; a confirmation review is recommended, not an automatic denial."
        )
    if attendance_follow_up_output.evidence.get("follow_up_status") == "due":
        parts.append("Operational note: a scheduled follow-up is due for this patient.")

    return " ".join(parts)
