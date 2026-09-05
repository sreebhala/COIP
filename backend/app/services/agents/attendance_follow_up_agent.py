"""
Attendance and Follow-up Agent — COIP-AFU-001 to COIP-AFU-005.

Boundary: does NOT infer patient behavior or health condition. This is the
agent flagged in the Post #1.1 Safety Boundary Review as highest-risk for
boundary drift, since it is structurally similar to a "risk" agent. Per
that review, this agent's output is always called an "attendance
indicator" — never "risk" — and is strictly count-based. When history is
insufficient, it explicitly withholds classification (COIP-AFU-005) rather
than guessing.
"""
from datetime import date, datetime, timedelta
from typing import Any

from app.schemas.common import AgentOutput
from app.services.agents.base import DeterministicAgent
from app.services.rules import catalogue as rules

AGENT_NAME = "AttendanceAndFollowUpAgent"


class AttendanceAndFollowUpAgent(DeterministicAgent):
    name = AGENT_NAME

    def run(self, context: dict[str, Any]) -> AgentOutput:
        request = context.get("appointment_request", {})
        attendance_summary = context.get("attendance_summary", {})
        follow_up_summary = context.get("follow_up_summary", {})

        rules_triggered: list[str] = []
        reason_codes: list[str] = []
        evidence: dict[str, Any] = {}

        # --- Confirmation need (COIP-AFU-001) ---------------------------------
        confirmation_action = "none_required"
        confirmation_status = request.get("confirmation_status")
        preferred_date_raw = request.get("preferred_date")
        if confirmation_status != "confirmed" and preferred_date_raw:
            preferred_date = (
                preferred_date_raw
                if isinstance(preferred_date_raw, date)
                else datetime.fromisoformat(preferred_date_raw).date()
            )
            within_48_hours = preferred_date <= date.today() + timedelta(days=2)
            if within_48_hours:
                confirmation_action = "confirm_before_visit"
                rules_triggered.append(rules.AFU_001_CONFIRMATION_REQUIRED.rule_id)
                reason_codes.append(rules.AFU_001_CONFIRMATION_REQUIRED.reason_code)
                evidence["confirmation_status"] = confirmation_status

        # --- Attendance indicator (COIP-AFU-002 / COIP-AFU-005) -----------------
        # Strictly count-based. Never a behavioral or health judgment.
        if not attendance_summary or attendance_summary.get("total_records", 0) == 0:
            attendance_indicator = "insufficient_history"
            rules_triggered.append(rules.AFU_005_INSUFFICIENT_HISTORY.rule_id)
            reason_codes.append(rules.AFU_005_INSUFFICIENT_HISTORY.reason_code)
        else:
            missed_count = attendance_summary.get("missed_count", 0)
            if missed_count >= 2:
                attendance_indicator = "repeated_missed_appointments"
                # Operational confirmation review only — never an automatic
                # denial of care, per COIP-AFU-002's documented result.
                if confirmation_action == "none_required":
                    confirmation_action = "confirmation_review"
                rules_triggered.append(rules.AFU_002_REPEATED_MISSED_APPOINTMENTS.rule_id)
                reason_codes.append(rules.AFU_002_REPEATED_MISSED_APPOINTMENTS.reason_code)
            else:
                attendance_indicator = "normal"
            evidence["attendance_summary"] = attendance_summary

        # --- Follow-up status (COIP-AFU-003 / COIP-AFU-004) --------------------
        if not follow_up_summary:
            follow_up_status = "none"
        elif follow_up_summary.get("is_overdue") or follow_up_summary.get("status") == "due":
            follow_up_status = "due"
            rules_triggered.append(rules.AFU_003_FOLLOW_UP_DUE.rule_id)
            reason_codes.append(rules.AFU_003_FOLLOW_UP_DUE.reason_code)
            evidence["follow_up_summary"] = follow_up_summary
        else:
            follow_up_status = "scheduled_no_duplicate_action"
            rules_triggered.append(rules.AFU_004_FOLLOW_UP_SCHEDULED.rule_id)
            reason_codes.append(rules.AFU_004_FOLLOW_UP_SCHEDULED.reason_code)
            evidence["follow_up_summary"] = follow_up_summary

        evidence["attendance_indicator"] = attendance_indicator
        evidence["confirmation_action"] = confirmation_action
        evidence["follow_up_status"] = follow_up_status

        return AgentOutput(
            agent_name=self.name,
            workflow_session_id=context.get("workflow_session_id", ""),
            appointment_request_id=context.get("appointment_request_id", ""),
            classification=attendance_indicator,
            recommendation=confirmation_action,
            reasons=reason_codes,
            rules_triggered=rules_triggered,
            evidence=evidence,
            context_updated=["attendance_follow_up_result"],
        )
