"""
COIP Workflow / Context endpoints — Post #1.3.

Implements exactly the three endpoints from the API Contract Guide relevant
to this post:

  POST /api/v1/workflows/appointment-review/context
  GET  /api/v1/workflows/{workflow_session_id}
  GET  /api/v1/workflows/{workflow_session_id}/context

No agents run yet (Post #1.4/#1.5). This route only builds and stores the
run-scoped context, and lets it be inspected afterward.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.core.database import get_db
from app.models.domain import AgentExecutionLog, WorkflowSession
from app.schemas.workflow import (
    ContextBuildRequest,
    ContextBuildResponse,
    EmergencyStopResponse,
    WorkflowSessionRead,
)
from app.services.context.context_builder import ContextBuilder
from app.services.context.exceptions import (
    AppointmentRequestNotFoundError,
    EmergencyRoutingRequiredError,
)

router = APIRouter(prefix="/api/v1/workflows", tags=["Workflows"])


def _next_workflow_session_id(db: Session) -> str:
    count = db.query(WorkflowSession).count()
    return f"WF-{count + 1:06d}"


@router.post("/appointment-review/context")
def build_appointment_review_context(payload: ContextBuildRequest, db: Session = Depends(get_db)):
    workflow_session_id = _next_workflow_session_id(db)

    session_row = WorkflowSession(
        workflow_session_id=workflow_session_id,
        appointment_request_id=payload.appointment_request_id,
        review_reason="appointment_review",
        status="in_progress",
        input_snapshot={"appointment_request_id": payload.appointment_request_id},
    )
    db.add(session_row)
    db.flush()

    builder = ContextBuilder(db)
    try:
        context = builder.build(workflow_session_id, payload.appointment_request_id)
    except AppointmentRequestNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Appointment request not found")
    except EmergencyRoutingRequiredError as exc:
        session_row.status = "emergency_stop"
        session_row.context_snapshot = {
            "routing_status": "emergency_stop",
            "appointment_request_id": payload.appointment_request_id,
        }
        db.commit()
        return EmergencyStopResponse(
            workflow_session_id=workflow_session_id,
            appointment_request_id=payload.appointment_request_id,
            message=str(exc),
        )

    session_row.status = context.routing_status
    session_row.context_snapshot = context.model_dump()
    db.commit()
    db.refresh(session_row)

    return ContextBuildResponse(
        workflow_session=WorkflowSessionRead(
            workflow_session_id=session_row.workflow_session_id,
            appointment_request_id=session_row.appointment_request_id,
            review_reason=session_row.review_reason,
            status=session_row.status,
            started_at=session_row.started_at,
            completed_at=session_row.completed_at,
        ),
        context=context,
    )


@router.get("/{workflow_session_id}", response_model=WorkflowSessionRead)
def get_workflow_session(workflow_session_id: str, db: Session = Depends(get_db)) -> WorkflowSessionRead:
    session_row = db.scalar(
        select(WorkflowSession).where(WorkflowSession.workflow_session_id == workflow_session_id)
    )
    if not session_row:
        raise HTTPException(status_code=404, detail="Workflow session not found")
    return WorkflowSessionRead(
        workflow_session_id=session_row.workflow_session_id,
        appointment_request_id=session_row.appointment_request_id,
        review_reason=session_row.review_reason,
        status=session_row.status,
        started_at=session_row.started_at,
        completed_at=session_row.completed_at,
    )


@router.get("/{workflow_session_id}/context")
def get_workflow_context(workflow_session_id: str, db: Session = Depends(get_db)):
    session_row = db.scalar(
        select(WorkflowSession).where(WorkflowSession.workflow_session_id == workflow_session_id)
    )
    if not session_row:
        raise HTTPException(status_code=404, detail="Workflow session not found")
    if not session_row.context_snapshot:
        raise HTTPException(status_code=404, detail="Context not yet available for this session")
    return session_row.context_snapshot


@router.get("/{workflow_session_id}/trace")
def get_workflow_trace(workflow_session_id: str, db: Session = Depends(get_db)):
    session_row = db.scalar(
        select(WorkflowSession).where(WorkflowSession.workflow_session_id == workflow_session_id)
    )
    if not session_row:
        raise HTTPException(status_code=404, detail="Workflow session not found")

    logs = db.scalars(
        select(AgentExecutionLog)
        .where(AgentExecutionLog.workflow_session_id == workflow_session_id)
        .order_by(AgentExecutionLog.sequence_number)
    ).all()

    return {
        "workflow_session_id": workflow_session_id,
        "agent_trace": [
            {
                "sequence_number": log.sequence_number,
                "agent_name": log.agent_name,
                "status": log.status,
                "input_summary": log.input_summary,
                "output_summary": log.output_summary,
                "rules_triggered": log.rules_triggered,
                "context_updated": log.context_updated,
            }
            for log in logs
        ],
    }
