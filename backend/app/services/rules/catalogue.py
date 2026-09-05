"""
COIP Deterministic Rule Catalogue — Post #1.4.

This module is the single source of truth for rule IDs and reason codes.
Agents reference these constants rather than hardcoding strings, so no
agent can silently drift from the approved Rule Catalogue.

Every rule here is operational only. None of these rules assess symptoms,
diagnoses, treatment, or clinical urgency.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    reason_code: str
    description: str


# --- Request Validation Rules (COIP-REQ) ------------------------------------
# COIP-REQ-005 (emergency) and COIP-REQ-006 (not found) are enforced by the
# Context Builder itself (Post #1.3), before any agent runs, since they are
# hard stops rather than evaluated conditions. This agent applies 001-004.
REQ_001_LOCATION_CLOSED = RuleDefinition(
    "COIP-REQ-001", "LOCATION_CLOSED",
    "Location inactive or preferred time outside operating hours.",
)
REQ_002_APPOINTMENT_IN_PAST = RuleDefinition(
    "COIP-REQ-002", "APPOINTMENT_IN_PAST",
    "Preferred date is in the past.",
)
REQ_003_APPOINTMENT_TYPE_MISSING = RuleDefinition(
    "COIP-REQ-003", "APPOINTMENT_TYPE_MISSING",
    "Appointment type missing or inactive.",
)
REQ_004_CONTACT_CHANNEL_MISSING = RuleDefinition(
    "COIP-REQ-004", "CONTACT_CHANNEL_MISSING",
    "No contact channel provided on the request.",
)
REQ_005_EMERGENCY_WORKFLOW_REQUIRED = RuleDefinition(
    "COIP-REQ-005", "EMERGENCY_WORKFLOW_REQUIRED",
    "Emergency flag entered by staff. Enforced by the Context Builder.",
)
REQ_006_REQUEST_NOT_FOUND = RuleDefinition(
    "COIP-REQ-006", "REQUEST_NOT_FOUND",
    "Patient/request not found. Enforced by the Context Builder.",
)

# --- Schedule Rules (COIP-SCH) ----------------------------------------------
SCH_001_REQUESTED_SLOT_AVAILABLE = RuleDefinition(
    "COIP-SCH-001", "REQUESTED_SLOT_AVAILABLE",
    "Requested doctor active and exact slot has capacity.",
)
SCH_002_FLEXIBILITY_AVAILABLE = RuleDefinition(
    "COIP-SCH-002", "FLEXIBILITY_AVAILABLE",
    "Exact slot full and patient flexibility is greater than zero.",
)
SCH_003_SAME_DOCTOR_ALTERNATIVE = RuleDefinition(
    "COIP-SCH-003", "SAME_DOCTOR_ALTERNATIVE",
    "Same doctor has a nearby slot with capacity.",
)
SCH_004_ALTERNATE_DOCTOR_AVAILABLE = RuleDefinition(
    "COIP-SCH-004", "ALTERNATE_DOCTOR_AVAILABLE",
    "An approved alternate doctor is available.",
)
SCH_005_NO_VALID_SLOT = RuleDefinition(
    "COIP-SCH-005", "NO_VALID_SLOT",
    "No valid slot found for this request.",
)

# --- Queue Rules (COIP-QUE) -------------------------------------------------
QUE_001_STABLE = RuleDefinition(
    "COIP-QUE-001", "QUEUE_STABLE", "Projected utilization <= 70%.",
)
QUE_002_BUSY = RuleDefinition(
    "COIP-QUE-002", "QUEUE_BUSY", "Projected utilization 71-90%.",
)
QUE_003_OVER_CAPACITY = RuleDefinition(
    "COIP-QUE-003", "QUEUE_OVER_CAPACITY", "Projected utilization > 90%.",
)
QUE_004_CONFIG_MISSING = RuleDefinition(
    "COIP-QUE-004", "QUEUE_CONFIG_MISSING", "Queue capacity configuration missing.",
)

# --- Resource Rules (COIP-RES) ----------------------------------------------
RES_001_REQUIRED_ROOM_AVAILABLE = RuleDefinition(
    "COIP-RES-001", "REQUIRED_ROOM_AVAILABLE", "Required room type is available.",
)
RES_002_LOWEST_LOAD_ROOM = RuleDefinition(
    "COIP-RES-002", "LOWEST_LOAD_ROOM", "Multiple rooms available; lowest-load room chosen.",
)
RES_003_ROOM_NOT_REQUIRED = RuleDefinition(
    "COIP-RES-003", "ROOM_NOT_REQUIRED", "No room required for this appointment type.",
)
RES_004_REQUIRED_ROOM_UNAVAILABLE = RuleDefinition(
    "COIP-RES-004", "REQUIRED_ROOM_UNAVAILABLE", "Required room type unavailable.",
)
RES_005_ROOM_CONFIG_MISSING = RuleDefinition(
    "COIP-RES-005", "ROOM_CONFIG_MISSING", "Room configuration missing for required type.",
)

# --- Attendance and Follow-up Rules (COIP-AFU) ------------------------------
AFU_001_CONFIRMATION_REQUIRED = RuleDefinition(
    "COIP-AFU-001", "CONFIRMATION_REQUIRED",
    "Appointment not confirmed and scheduled within 48 hours.",
)
AFU_002_REPEATED_MISSED_APPOINTMENTS = RuleDefinition(
    "COIP-AFU-002", "REPEATED_MISSED_APPOINTMENTS",
    "Two or more missed appointments in recent operational records.",
)
AFU_003_FOLLOW_UP_DUE = RuleDefinition(
    "COIP-AFU-003", "FOLLOW_UP_DUE", "Follow-up due date is today or overdue.",
)
AFU_004_FOLLOW_UP_SCHEDULED = RuleDefinition(
    "COIP-AFU-004", "FOLLOW_UP_SCHEDULED", "Follow-up already scheduled; no duplicate action.",
)
AFU_005_INSUFFICIENT_HISTORY = RuleDefinition(
    "COIP-AFU-005", "INSUFFICIENT_ATTENDANCE_HISTORY",
    "Insufficient attendance history; no classification made.",
)
