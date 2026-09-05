"""
Appointment Operations Decision Agent — Final Decision Precedence 1-8.

This is the only agent authorized to produce the final decision. All other
agents produce evidence only. Precedence 1 (emergency) and part of 2/3 (not
found / invalid request already caught upstream) are enforced before this
agent ever runs, by the Context Builder (Post #1.3). This agent applies
precedence 2 (invalid request) through 8.

Boundary: does not create clinical priority or diagnosis. Precedence rule
#8 ("No clinical prioritization is performed") is a hard structural
constraint — no branch in this agent references health, symptoms, or
diagnosis in any way.
"""
from typing import Any

from app.schemas.common import AgentOutput

AGENT_NAME = "AppointmentOperationsDecisionAgent"

DECISION_CONFIRM_SLOT = "Confirm Slot"
DECISION_SUGGEST_ALTERNATIVE = "Suggest Alternative"
DECISION_AWAIT_CONFIRMATION = "Await Confirmation"
DECISION_NEEDS_REVIEW = "Needs Review"
DECISION_REJECT = "Reject"


class AppointmentOperationsDecisionAgent:
    name = AGENT_NAME

    def run(
        self,
        context: dict[str, Any],
        request_validation: AgentOutput,
        schedule: AgentOutput,
        queue: AgentOutput,
        resource: AgentOutput,
        attendance_follow_up: AgentOutput,
    ) -> AgentOutput:
        reason_codes: list[str] = []
        rules_triggered: list[str] = []
        evidence: dict[str, Any] = {
            "request_validation": request_validation.classification,
            "schedule": schedule.classification,
            "queue": queue.classification,
            "resource": resource.classification,
            "attendance_follow_up": attendance_follow_up.classification,
        }

        def collect(agent_output: AgentOutput) -> None:
            reason_codes.extend(agent_output.reasons)
            rules_triggered.extend(agent_output.rules_triggered)

        # Precedence 2: invalid request or past date -> Reject.
        if request_validation.classification == "invalid":
            collect(request_validation)
            decision = DECISION_REJECT

        # Precedence 3: missing critical configuration -> Needs Review.
        elif queue.classification == "Missing Configuration" or resource.classification == "Needs Review":
            collect(request_validation)
            collect(queue)
            collect(resource)
            decision = DECISION_NEEDS_REVIEW

        else:
            exact_slot = schedule.classification == "Exact Slot Available"
            queue_acceptable = queue.classification in ("Stable", "Busy")
            resource_ok = resource.classification in ("Room Recommended", "Not Required")
            confirmation_needed = attendance_follow_up.recommendation == "confirm_before_visit"

            # Precedence 5: exact slot available but confirmation needed ->
            # Await Confirmation. Checked before Confirm Slot, matching the
            # documented precedence order (5 before 4 in effect, since an
            # exact-slot match with confirmation needed must not silently
            # become Confirm Slot).
            if exact_slot and queue_acceptable and resource_ok and confirmation_needed:
                collect(attendance_follow_up)
                decision = DECISION_AWAIT_CONFIRMATION

            # Precedence 4: exact slot + acceptable queue + required room ->
            # Confirm Slot.
            elif exact_slot and queue_acceptable and resource_ok:
                collect(schedule)
                collect(queue)
                collect(resource)
                decision = DECISION_CONFIRM_SLOT

            # Precedence 6: exact slot unavailable (or queue/resource forced
            # us away from it) but a valid alternative exists -> Suggest
            # Alternative.
            elif schedule.classification == "Alternative Slot Suggested":
                collect(schedule)
                decision = DECISION_SUGGEST_ALTERNATIVE

            elif exact_slot and not queue_acceptable:
                # Queue over capacity even though the doctor slot is
                # technically free — do not confirm; there is no
                # alternative slot evidence, so this needs human review.
                collect(schedule)
                collect(queue)
                decision = DECISION_NEEDS_REVIEW

            # Precedence 7: no valid slot/resource -> Needs Review.
            else:
                collect(schedule)
                collect(resource)
                decision = DECISION_NEEDS_REVIEW

        # Follow-up due status is always surfaced as an additional reason,
        # never as a factor that changes the operational decision itself,
        # per Scenario 6 ("include Follow-up Due reason without clinical
        # interpretation").
        if "FOLLOW_UP_DUE" in attendance_follow_up.reasons and "FOLLOW_UP_DUE" not in reason_codes:
            reason_codes.append("FOLLOW_UP_DUE")

        # Repeated missed appointments is always surfaced as an additional
        # reason too, but per COIP-AFU-002 must never by itself deny care —
        # it never changes `decision` above, only adds visibility.
        if (
            "REPEATED_MISSED_APPOINTMENTS" in attendance_follow_up.reasons
            and "REPEATED_MISSED_APPOINTMENTS" not in reason_codes
        ):
            reason_codes.append("REPEATED_MISSED_APPOINTMENTS")

        return AgentOutput(
            agent_name=self.name,
            workflow_session_id=context.get("workflow_session_id", ""),
            appointment_request_id=context.get("appointment_request_id", ""),
            classification=decision,
            recommendation=decision,
            reasons=reason_codes,
            rules_triggered=rules_triggered,
            evidence=evidence,
            context_updated=["appointment_decision_result"],
        )
