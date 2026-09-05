"""
Appointment Review Orchestrator — Post #1.5.

Coordinates the full deterministic workflow:

  Context Builder -> Appointment Request Agent -> Schedule Availability Agent
  -> Queue Load Agent -> Resource Allocation Agent -> Attendance/Follow-up
  Agent -> Appointment Operations Decision Agent -> Explanation Service ->
  Audit Service

Plain Python orchestration only. No LangGraph, no LLM. Every agent call is
logged to AgentExecutionLog in true execution order, so the trace always
reflects what actually ran, never an assumed sequence.

Emergency stop and unknown-request handling are enforced by the Context
Builder (Post #1.3) before any agent in this orchestrator ever runs.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import AgentExecutionLog, WorkflowSession
from app.services import audit_service
from app.services.agents.appointment_operations_decision_agent import AppointmentOperationsDecisionAgent
from app.services.agents.appointment_request_agent import AppointmentRequestAgent
from app.services.agents.attendance_follow_up_agent import AttendanceAndFollowUpAgent
from app.services.agents.queue_load_agent import QueueLoadAgent
from app.services.agents.resource_allocation_agent import ResourceAllocationAgent
from app.services.agents.schedule_availability_agent import ScheduleAvailabilityAgent
from app.services.context.context_builder import ContextBuilder
from app.services.context.exceptions import AppointmentRequestNotFoundError, EmergencyRoutingRequiredError
from app.services.explanation_service import build_explanation

APPROVED_SEQUENCE = [
    AppointmentRequestAgent,
    ScheduleAvailabilityAgent,
    QueueLoadAgent,
    ResourceAllocationAgent,
    AttendanceAndFollowUpAgent,
]


def _next_workflow_session_id(db: Session) -> str:
    count = db.query(WorkflowSession).count()
    return f"WF-{count + 1:06d}"


def _log_agent_run(
    db: Session,
    workflow_session_id: str,
    sequence_number: int,
    agent_output,
    input_summary: dict | None = None,
) -> None:
    db.add(
        AgentExecutionLog(
            workflow_session_id=workflow_session_id,
            agent_name=agent_output.agent_name,
            sequence_number=sequence_number,
            status="completed",
            input_summary=input_summary or {},
            output_summary={
                "classification": agent_output.classification,
                "recommendation": agent_output.recommendation,
            },
            rules_triggered=agent_output.rules_triggered,
            context_updated=agent_output.context_updated,
            completed_at=datetime.now(timezone.utc),
        )
    )


class AppointmentReviewOrchestrator:
    def __init__(self, db: Session):
        self.db = db

    def run(self, appointment_request_id: str, review_reason: str = "appointment_review") -> dict:
        workflow_session_id = _next_workflow_session_id(self.db)
        session_row = WorkflowSession(
            workflow_session_id=workflow_session_id,
            appointment_request_id=appointment_request_id,
            review_reason=review_reason,
            status="in_progress",
            input_snapshot={"appointment_request_id": appointment_request_id},
        )
        self.db.add(session_row)
        self.db.flush()

        builder = ContextBuilder(self.db)
        try:
            context = builder.build(workflow_session_id, appointment_request_id)
        except AppointmentRequestNotFoundError:
            self.db.rollback()
            raise
        except EmergencyRoutingRequiredError as exc:
            session_row.status = "emergency_stop"
            session_row.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            return {
                "workflow_session_id": workflow_session_id,
                "appointment_request_id": appointment_request_id,
                "status": "emergency_stop",
                "message": str(exc),
            }

        ctx = context.model_dump()

        req_output = AppointmentRequestAgent().run(ctx)
        _log_agent_run(self.db, workflow_session_id, 1, req_output, input_summary={
            "appointment_request": ctx.get("appointment_request"),
            "location": ctx.get("location"),
            "appointment_type": ctx.get("appointment_type"),
        })

        sch_output = ScheduleAvailabilityAgent().run(ctx)
        _log_agent_run(self.db, workflow_session_id, 2, sch_output, input_summary={
            "requested_doctor": ctx.get("requested_doctor"),
            "doctor_availability": ctx.get("doctor_availability"),
            "existing_appointments_count": len(ctx.get("existing_appointments", [])),
            "flexibility_minutes": ctx.get("appointment_request", {}).get("flexibility_minutes"),
        })

        que_output = QueueLoadAgent().run(ctx)
        _log_agent_run(self.db, workflow_session_id, 3, que_output, input_summary={
            "queue_snapshot": ctx.get("queue_snapshot"),
        })

        res_output = ResourceAllocationAgent().run(ctx)
        _log_agent_run(self.db, workflow_session_id, 4, res_output, input_summary={
            "required_room_type": ctx.get("appointment_type", {}).get("required_room_type"),
            "rooms": ctx.get("rooms"),
        })

        afu_output = AttendanceAndFollowUpAgent().run(ctx)
        _log_agent_run(self.db, workflow_session_id, 5, afu_output, input_summary={
            "confirmation_status": ctx.get("appointment_request", {}).get("confirmation_status"),
            "attendance_summary": ctx.get("attendance_summary"),
            "follow_up_summary": ctx.get("follow_up_summary"),
        })

        decision_output = AppointmentOperationsDecisionAgent().run(
            ctx, req_output, sch_output, que_output, res_output, afu_output
        )
        _log_agent_run(self.db, workflow_session_id, 6, decision_output, input_summary={
            "request_validation": req_output.classification,
            "schedule": sch_output.classification,
            "queue": que_output.classification,
            "resource": res_output.classification,
            "attendance_follow_up": afu_output.classification,
        })

        explanation = build_explanation(
            decision_output.classification, sch_output, que_output, res_output, afu_output
        )

        all_reason_codes = list(dict.fromkeys(decision_output.reasons))  # de-duplicated, order-preserved

        evidence_snapshot = {
            "request_validation": req_output.evidence,
            "schedule": sch_output.evidence,
            "queue": que_output.evidence,
            "resource": res_output.evidence,
            "attendance_follow_up": afu_output.evidence,
        }

        decision_record = audit_service.record_decision(
            self.db,
            workflow_session_id=workflow_session_id,
            appointment_request_id=appointment_request_id,
            decision_category=decision_output.classification,
            recommendation=decision_output.recommendation,
            reason_codes=all_reason_codes,
            evidence_snapshot=evidence_snapshot,
            explanation=explanation,
        )

        # --- Response, built to match the documented Review Response Shape ---
        queue_evidence = que_output.evidence
        wait_band = None
        if que_output.recommendation:
            # QueueLoadAgent.recommendation is already "{low}-{high} minutes (estimate)"
            wait_band = que_output.recommendation.replace(" minutes (estimate)", "")

        response = {
            "workflow_session_id": workflow_session_id,
            "appointment_request_id": appointment_request_id,
            "status": "completed",
            "request_validation": {"status": req_output.classification},
            "schedule": {
                "category": sch_output.classification,
                "doctor_code": ctx.get("requested_doctor", {}).get("doctor_code"),
                "date": ctx.get("appointment_request", {}).get("preferred_date"),
                "time": sch_output.recommendation
                if sch_output.classification == "Exact Slot Available"
                else ctx.get("appointment_request", {}).get("preferred_time"),
            },
            "queue": {
                "category": que_output.classification,
                "projected_utilization_percent": queue_evidence.get("projected_utilization_percent"),
                "estimated_wait_band_minutes": wait_band,
            },
            "resource": {"room_code": res_output.recommendation},
            "attendance_follow_up": {
                "confirmation_action": afu_output.recommendation,
                "follow_up_status": afu_output.evidence.get("follow_up_status"),
            },
            "decision": {"category": decision_output.classification},
            "reason_codes": all_reason_codes,
            "agent_trace": [
                {"agent": o.agent_name, "classification": o.classification, "rules_triggered": o.rules_triggered}
                for o in (req_output, sch_output, que_output, res_output, afu_output, decision_output)
            ],
            "explanation": explanation,
            "audit_reference": decision_record.audit_reference,
        }

        session_row.status = "completed"
        session_row.context_snapshot = context.model_dump()
        session_row.final_output_snapshot = response
        session_row.completed_at = datetime.now(timezone.utc)
        self.db.commit()

        return response
