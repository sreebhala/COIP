"""
Appointment Request Agent — COIP-REQ-001 to COIP-REQ-004.

COIP-REQ-005 (emergency) and COIP-REQ-006 (not found) are already enforced
by the Context Builder before this agent ever runs — this agent never sees
an emergency-flagged or unknown request.

Boundary: does not assess symptoms or clinical urgency. Only validates
location status/hours, date validity, appointment type status, and contact
channel presence.
"""
from datetime import date, datetime
from typing import Any

from app.schemas.common import AgentOutput
from app.services.agents.base import DeterministicAgent
from app.services.rules import catalogue as rules

AGENT_NAME = "AppointmentRequestAgent"


class AppointmentRequestAgent(DeterministicAgent):
    name = AGENT_NAME

    def run(self, context: dict[str, Any]) -> AgentOutput:
        request = context.get("appointment_request", {})
        location = context.get("location", {})
        appointment_type = context.get("appointment_type", {})

        rules_triggered: list[str] = []
        reason_codes: list[str] = []
        evidence: dict[str, Any] = {}
        valid = True

        # COIP-REQ-001: location inactive or outside operating hours
        if location:
            preferred_time = request.get("preferred_time", "")
            opening = location.get("opening_time")
            closing = location.get("closing_time")
            location_closed = (not location.get("active", True)) or (
                opening and closing and not (opening <= preferred_time <= closing)
            )
            if location_closed:
                valid = False
                rules_triggered.append(rules.REQ_001_LOCATION_CLOSED.rule_id)
                reason_codes.append(rules.REQ_001_LOCATION_CLOSED.reason_code)
                evidence["location_status"] = {
                    "active": location.get("active"),
                    "opening_time": opening,
                    "closing_time": closing,
                    "preferred_time": preferred_time,
                }

        # COIP-REQ-002: preferred date in the past
        preferred_date_raw = request.get("preferred_date")
        if preferred_date_raw:
            preferred_date = (
                preferred_date_raw
                if isinstance(preferred_date_raw, date)
                else datetime.fromisoformat(preferred_date_raw).date()
            )
            if preferred_date < date.today():
                valid = False
                rules_triggered.append(rules.REQ_002_APPOINTMENT_IN_PAST.rule_id)
                reason_codes.append(rules.REQ_002_APPOINTMENT_IN_PAST.reason_code)
                evidence["preferred_date"] = preferred_date_raw

        # COIP-REQ-003: appointment type missing or inactive
        if not appointment_type or not appointment_type.get("active", False):
            valid = False
            rules_triggered.append(rules.REQ_003_APPOINTMENT_TYPE_MISSING.rule_id)
            reason_codes.append(rules.REQ_003_APPOINTMENT_TYPE_MISSING.reason_code)
            evidence["appointment_type"] = appointment_type or None

        # COIP-REQ-004: no contact channel
        if not request.get("contact_channel"):
            # Await Information, not a rejection — recorded but does not by
            # itself invalidate the request.
            rules_triggered.append(rules.REQ_004_CONTACT_CHANNEL_MISSING.rule_id)
            reason_codes.append(rules.REQ_004_CONTACT_CHANNEL_MISSING.reason_code)
            evidence["contact_channel"] = request.get("contact_channel")

        classification = "valid" if valid else "invalid"

        return AgentOutput(
            agent_name=self.name,
            workflow_session_id=context.get("workflow_session_id", ""),
            appointment_request_id=context.get("appointment_request_id", ""),
            classification=classification,
            recommendation=None,
            reasons=reason_codes,
            rules_triggered=rules_triggered,
            evidence=evidence,
            context_updated=["request_validation_result"],
        )
