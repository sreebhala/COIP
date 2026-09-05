"""
Queue Load Agent — COIP-QUE-001 to COIP-QUE-004.

Boundary: operational load only, never a clinical urgency signal. The
estimated wait band is explicitly an estimate, never presented as
guaranteed, per the Required/Avoid language table in the Safety Guide.
"""
from typing import Any

from app.schemas.common import AgentOutput
from app.services.agents.base import DeterministicAgent
from app.services.rules import catalogue as rules

AGENT_NAME = "QueueLoadAgent"


class QueueLoadAgent(DeterministicAgent):
    name = AGENT_NAME

    def run(self, context: dict[str, Any]) -> AgentOutput:
        queue_snapshot = context.get("queue_snapshot", {})
        appointment_type = context.get("appointment_type", {})

        rules_triggered: list[str] = []
        reason_codes: list[str] = []
        evidence: dict[str, Any] = {}

        if not queue_snapshot:
            category = "Missing Configuration"
            rules_triggered.append(rules.QUE_004_CONFIG_MISSING.rule_id)
            reason_codes.append(rules.QUE_004_CONFIG_MISSING.reason_code)
            return AgentOutput(
                agent_name=self.name,
                workflow_session_id=context.get("workflow_session_id", ""),
                appointment_request_id=context.get("appointment_request_id", ""),
                classification=category,
                recommendation=None,
                reasons=reason_codes,
                rules_triggered=rules_triggered,
                evidence=evidence,
                context_updated=["queue_result"],
            )

        operational_capacity = max(queue_snapshot.get("operational_capacity", 1), 1)
        booked_count = queue_snapshot.get("booked_count", 0)
        waiting_count = queue_snapshot.get("waiting_count", 0)
        projected_utilization = round((booked_count + waiting_count) / operational_capacity * 100)

        if projected_utilization <= 70:
            category = "Stable"
            rules_triggered.append(rules.QUE_001_STABLE.rule_id)
            reason_codes.append(rules.QUE_001_STABLE.reason_code)
        elif projected_utilization <= 90:
            category = "Busy"
            rules_triggered.append(rules.QUE_002_BUSY.rule_id)
            reason_codes.append(rules.QUE_002_BUSY.reason_code)
        else:
            category = "Over Capacity"
            rules_triggered.append(rules.QUE_003_OVER_CAPACITY.rule_id)
            reason_codes.append(rules.QUE_003_OVER_CAPACITY.reason_code)

        # Estimated wait band — derived, never guaranteed. Uses the
        # appointment type's configured default duration as a proxy average
        # service time (Phase 1 documented assumption: no separately
        # configured average-service-time field exists yet).
        avg_service_minutes = appointment_type.get("default_duration_minutes", 20)
        low = waiting_count * avg_service_minutes
        high = (waiting_count + 1) * avg_service_minutes
        wait_band = f"{low}-{high} minutes (estimate)"

        evidence["projected_utilization_percent"] = projected_utilization
        evidence["queue_snapshot"] = queue_snapshot

        return AgentOutput(
            agent_name=self.name,
            workflow_session_id=context.get("workflow_session_id", ""),
            appointment_request_id=context.get("appointment_request_id", ""),
            classification=category,
            recommendation=wait_band,
            score=min(projected_utilization, 100),
            reasons=reason_codes,
            rules_triggered=rules_triggered,
            evidence=evidence,
            context_updated=["queue_result"],
        )
