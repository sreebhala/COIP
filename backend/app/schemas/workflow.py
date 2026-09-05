from datetime import datetime
from pydantic import BaseModel

from app.services.context.base import SharedWorkflowContext


class ContextBuildRequest(BaseModel):
    appointment_request_id: str


class WorkflowSessionRead(BaseModel):
    workflow_session_id: str
    appointment_request_id: str
    review_reason: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None


class ContextBuildResponse(BaseModel):
    workflow_session: WorkflowSessionRead
    context: SharedWorkflowContext


class EmergencyStopResponse(BaseModel):
    workflow_session_id: str
    appointment_request_id: str
    status: str = "emergency_stop"
    message: str
