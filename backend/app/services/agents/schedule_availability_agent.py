"""
Schedule Availability Agent — COIP-SCH-001 to COIP-SCH-005.

Boundary: does not choose based on clinical severity. Ranking is based only
on same-doctor-first, then approved alternate doctors, per the Rule
Catalogue. Phase 1 limitation (documented, not hidden): alternative-doctor
availability is confirmed only by presence in context.alternative_doctors
(location + specialty match); a full per-doctor slot search for alternates
is out of scope for Phase 1 and left as a Phase 1.5+ enhancement.
"""
from typing import Any

from app.schemas.common import AgentOutput
from app.services.agents.base import DeterministicAgent
from app.services.rules import catalogue as rules

AGENT_NAME = "ScheduleAvailabilityAgent"


def _window_for_time(availability: list[dict], time_value: str) -> dict | None:
    for window in availability:
        if window["start_time"] <= time_value < window["end_time"]:
            return window
    return None


def _count_in_window(existing_appointments: list[dict], window: dict) -> int:
    return sum(
        1
        for appt in existing_appointments
        if window["start_time"] <= appt["start_time"] < window["end_time"]
        and appt.get("status") != "cancelled"
    )


class ScheduleAvailabilityAgent(DeterministicAgent):
    name = AGENT_NAME

    def run(self, context: dict[str, Any]) -> AgentOutput:
        request = context.get("appointment_request", {})
        requested_doctor = context.get("requested_doctor", {})
        availability = context.get("doctor_availability", [])
        existing_appointments = context.get("existing_appointments", [])
        alternative_doctors = context.get("alternative_doctors", [])
        flexibility_minutes = request.get("flexibility_minutes", 0)
        preferred_time = request.get("preferred_time", "")

        rules_triggered: list[str] = []
        reason_codes: list[str] = []
        evidence: dict[str, Any] = {}
        category = "No Valid Slot"
        recommendation = None

        if not requested_doctor:
            rules_triggered.append(rules.SCH_005_NO_VALID_SLOT.rule_id)
            reason_codes.append(rules.SCH_005_NO_VALID_SLOT.reason_code)
            evidence["reason"] = "no_requested_doctor"
        else:
            window = _window_for_time(availability, preferred_time)
            exact_available = False
            if window:
                booked_in_window = _count_in_window(existing_appointments, window)
                exact_available = booked_in_window < window["maximum_appointments"]
                evidence["exact_window"] = window
                evidence["booked_in_window"] = booked_in_window

            if exact_available:
                category = "Exact Slot Available"
                recommendation = preferred_time
                rules_triggered.append(rules.SCH_001_REQUESTED_SLOT_AVAILABLE.rule_id)
                reason_codes.append(rules.SCH_001_REQUESTED_SLOT_AVAILABLE.reason_code)
            else:
                # Exact slot full or not configured for this time.
                if flexibility_minutes > 0:
                    rules_triggered.append(rules.SCH_002_FLEXIBILITY_AVAILABLE.rule_id)
                    reason_codes.append(rules.SCH_002_FLEXIBILITY_AVAILABLE.reason_code)

                    # Same-doctor alternative: any other configured window on
                    # the same date with spare capacity.
                    same_doctor_alt = None
                    for candidate_window in availability:
                        if candidate_window is window:
                            continue
                        if _count_in_window(existing_appointments, candidate_window) < candidate_window["maximum_appointments"]:
                            same_doctor_alt = candidate_window
                            break

                    if same_doctor_alt:
                        category = "Alternative Slot Suggested"
                        recommendation = same_doctor_alt["start_time"]
                        rules_triggered.append(rules.SCH_003_SAME_DOCTOR_ALTERNATIVE.rule_id)
                        reason_codes.append(rules.SCH_003_SAME_DOCTOR_ALTERNATIVE.reason_code)
                        evidence["same_doctor_alternative_window"] = same_doctor_alt
                    elif alternative_doctors:
                        category = "Alternative Slot Suggested"
                        recommendation = alternative_doctors[0]["doctor_code"]
                        rules_triggered.append(rules.SCH_004_ALTERNATE_DOCTOR_AVAILABLE.rule_id)
                        reason_codes.append(rules.SCH_004_ALTERNATE_DOCTOR_AVAILABLE.reason_code)
                        evidence["alternate_doctor"] = alternative_doctors[0]
                    else:
                        rules_triggered.append(rules.SCH_005_NO_VALID_SLOT.rule_id)
                        reason_codes.append(rules.SCH_005_NO_VALID_SLOT.reason_code)
                else:
                    rules_triggered.append(rules.SCH_005_NO_VALID_SLOT.rule_id)
                    reason_codes.append(rules.SCH_005_NO_VALID_SLOT.reason_code)

        return AgentOutput(
            agent_name=self.name,
            workflow_session_id=context.get("workflow_session_id", ""),
            appointment_request_id=context.get("appointment_request_id", ""),
            classification=category,
            recommendation=recommendation,
            reasons=reason_codes,
            rules_triggered=rules_triggered,
            evidence=evidence,
            context_updated=["schedule_result"],
        )
