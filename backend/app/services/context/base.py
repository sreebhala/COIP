from typing import Any
from pydantic import BaseModel, Field

class SharedWorkflowContext(BaseModel):
    workflow_session_id: str
    appointment_request_id: str
    review_reason: str = "appointment_review"
    appointment_request: dict[str, Any] = Field(default_factory=dict)
    patient_profile: dict[str, Any] = Field(default_factory=dict)
    clinic: dict[str, Any] = Field(default_factory=dict)
    location: dict[str, Any] = Field(default_factory=dict)
    appointment_type: dict[str, Any] = Field(default_factory=dict)
    requested_doctor: dict[str, Any] = Field(default_factory=dict)
    doctor_availability: list[dict[str, Any]] = Field(default_factory=list)
    alternative_doctors: list[dict[str, Any]] = Field(default_factory=list)
    existing_appointments: list[dict[str, Any]] = Field(default_factory=list)
    queue_snapshot: dict[str, Any] = Field(default_factory=dict)
    rooms: list[dict[str, Any]] = Field(default_factory=list)
    attendance_summary: dict[str, Any] = Field(default_factory=dict)
    follow_up_summary: dict[str, Any] = Field(default_factory=dict)
    agent_outputs: dict[str, Any] = Field(default_factory=dict)
    final_decision: dict[str, Any] = Field(default_factory=dict)
    explanation: str = ""
    audit_status: str = "pending"
    audit_reference: str | None = None

    # Post #1.3 additions — run-scoped context lifecycle tracking only.
    # This context is populated fresh for every workflow session; it is
    # never treated as durable long-term memory for a patient or doctor.
    routing_status: str = "in_progress"
    # One of: "in_progress", "context_ready", "emergency_stop",
    # "invalid_request", "missing_configuration".
    missing_data_flags: list[str] = Field(default_factory=list)
    # Explicit, human-readable flags for any configuration or reference
    # data that was expected but not found (e.g. "no_doctor_availability_
    # configured"). Never silently left blank — always recorded here so a
    # reviewer can see exactly what was missing.

