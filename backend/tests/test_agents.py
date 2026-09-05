"""
Post #1.4 required tests: every rule, exact slot, alternative slot, queue
boundaries, resource conflict, await confirmation, follow-up due, repeated
missed appointments, unknown/invalid request, and no clinical outputs.

Emergency-flag and unknown-request behavior at the workflow level is
already covered by tests/test_context_builder.py (Post #1.3), since those
are enforced by the Context Builder before any agent here runs. This file
focuses on the six agents themselves.
"""
import json

from app.services.agents.appointment_operations_decision_agent import (
    AppointmentOperationsDecisionAgent,
    DECISION_AWAIT_CONFIRMATION,
    DECISION_CONFIRM_SLOT,
    DECISION_NEEDS_REVIEW,
    DECISION_REJECT,
    DECISION_SUGGEST_ALTERNATIVE,
)
from app.services.agents.appointment_request_agent import AppointmentRequestAgent
from app.services.agents.attendance_follow_up_agent import AttendanceAndFollowUpAgent
from app.services.agents.queue_load_agent import QueueLoadAgent
from app.services.agents.resource_allocation_agent import ResourceAllocationAgent
from app.services.agents.schedule_availability_agent import ScheduleAvailabilityAgent

BASE_CONTEXT = {
    "workflow_session_id": "WF-TEST",
    "appointment_request_id": "REQ-TEST",
    "appointment_request": {
        "preferred_date": "2099-01-10",
        "preferred_time": "10:00",
        "flexibility_minutes": 0,
        "contact_channel": "phone",
        "confirmation_status": "confirmed",
    },
    "location": {"active": True, "opening_time": "08:00", "closing_time": "20:00"},
    "appointment_type": {"active": True, "required_room_type": "consultation", "default_duration_minutes": 20},
    "requested_doctor": {"doctor_code": "DOC-001"},
    "doctor_availability": [
        {"start_time": "09:00", "end_time": "13:00", "maximum_appointments": 2},
    ],
    "existing_appointments": [],
    "alternative_doctors": [],
    "queue_snapshot": {"booked_count": 3, "waiting_count": 0, "operational_capacity": 10},
    "rooms": [{"room_code": "ROOM-01", "room_type": "consultation"}],
    "attendance_summary": {"total_records": 3, "attended_count": 2, "missed_count": 1},
    "follow_up_summary": {},
}


def deep_copy(d):
    return json.loads(json.dumps(d))


# --- Appointment Request Agent (COIP-REQ-001 to 004) ------------------------

def test_req_valid_request_passes():
    output = AppointmentRequestAgent().run(deep_copy(BASE_CONTEXT))
    assert output.classification == "valid"
    assert "COIP-REQ-001" not in output.rules_triggered


def test_req_001_location_closed():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["location"]["active"] = False
    output = AppointmentRequestAgent().run(ctx)
    assert output.classification == "invalid"
    assert "COIP-REQ-001" in output.rules_triggered
    assert "LOCATION_CLOSED" in output.reasons


def test_req_002_appointment_in_past():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["appointment_request"]["preferred_date"] = "2000-01-01"
    output = AppointmentRequestAgent().run(ctx)
    assert output.classification == "invalid"
    assert "COIP-REQ-002" in output.rules_triggered
    assert "APPOINTMENT_IN_PAST" in output.reasons


def test_req_003_appointment_type_missing():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["appointment_type"] = {}
    output = AppointmentRequestAgent().run(ctx)
    assert output.classification == "invalid"
    assert "COIP-REQ-003" in output.rules_triggered


def test_req_004_contact_channel_missing_does_not_invalidate():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["appointment_request"]["contact_channel"] = None
    output = AppointmentRequestAgent().run(ctx)
    assert "COIP-REQ-004" in output.rules_triggered
    assert output.classification == "valid"  # await information, not reject


# --- Schedule Availability Agent (COIP-SCH-001 to 005) -----------------------

def test_sch_001_exact_slot_available():
    output = ScheduleAvailabilityAgent().run(deep_copy(BASE_CONTEXT))
    assert output.classification == "Exact Slot Available"
    assert "COIP-SCH-001" in output.rules_triggered


def test_sch_002_003_alternative_slot_same_doctor():
    ctx = deep_copy(BASE_CONTEXT)
    # Fill the exact requested window to capacity.
    ctx["existing_appointments"] = [
        {"start_time": "10:00", "status": "confirmed"},
        {"start_time": "10:00", "status": "confirmed"},
    ]
    ctx["appointment_request"]["flexibility_minutes"] = 60
    ctx["doctor_availability"].append(
        {"start_time": "14:00", "end_time": "18:00", "maximum_appointments": 2}
    )
    output = ScheduleAvailabilityAgent().run(ctx)
    assert output.classification == "Alternative Slot Suggested"
    assert "COIP-SCH-002" in output.rules_triggered
    assert "COIP-SCH-003" in output.rules_triggered


def test_sch_004_alternate_doctor_available():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["existing_appointments"] = [
        {"start_time": "10:00", "status": "confirmed"},
        {"start_time": "10:00", "status": "confirmed"},
    ]
    ctx["appointment_request"]["flexibility_minutes"] = 60
    ctx["doctor_availability"] = [ctx["doctor_availability"][0]]  # only one, now full
    ctx["alternative_doctors"] = [{"doctor_code": "DOC-002", "full_name": "Dr. Alt"}]
    output = ScheduleAvailabilityAgent().run(ctx)
    assert output.classification == "Alternative Slot Suggested"
    assert "COIP-SCH-004" in output.rules_triggered


def test_sch_005_no_valid_slot():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["existing_appointments"] = [
        {"start_time": "10:00", "status": "confirmed"},
        {"start_time": "10:00", "status": "confirmed"},
    ]
    ctx["appointment_request"]["flexibility_minutes"] = 0
    output = ScheduleAvailabilityAgent().run(ctx)
    assert output.classification == "No Valid Slot"
    assert "COIP-SCH-005" in output.rules_triggered


# --- Queue Load Agent (COIP-QUE-001 to 004) ----------------------------------

def test_que_001_stable_boundary():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["queue_snapshot"] = {"booked_count": 7, "waiting_count": 0, "operational_capacity": 10}  # 70%
    output = QueueLoadAgent().run(ctx)
    assert output.classification == "Stable"
    assert "COIP-QUE-001" in output.rules_triggered


def test_que_002_busy_boundary():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["queue_snapshot"] = {"booked_count": 8, "waiting_count": 0, "operational_capacity": 10}  # 80%
    output = QueueLoadAgent().run(ctx)
    assert output.classification == "Busy"
    assert "COIP-QUE-002" in output.rules_triggered


def test_que_003_over_capacity_boundary():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["queue_snapshot"] = {"booked_count": 10, "waiting_count": 1, "operational_capacity": 10}  # 110%
    output = QueueLoadAgent().run(ctx)
    assert output.classification == "Over Capacity"
    assert "COIP-QUE-003" in output.rules_triggered


def test_que_004_config_missing():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["queue_snapshot"] = {}
    output = QueueLoadAgent().run(ctx)
    assert output.classification == "Missing Configuration"
    assert "COIP-QUE-004" in output.rules_triggered


def test_que_wait_band_is_labeled_as_estimate():
    output = QueueLoadAgent().run(deep_copy(BASE_CONTEXT))
    assert "estimate" in output.recommendation.lower()


# --- Resource Allocation Agent (COIP-RES-001 to 005) --------------------------

def test_res_001_room_available():
    output = ResourceAllocationAgent().run(deep_copy(BASE_CONTEXT))
    assert output.classification == "Room Recommended"
    assert "COIP-RES-001" in output.rules_triggered


def test_res_002_lowest_load_room_flagged_with_multiple_rooms():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["rooms"] = [
        {"room_code": "ROOM-01", "room_type": "consultation"},
        {"room_code": "ROOM-02", "room_type": "consultation"},
    ]
    output = ResourceAllocationAgent().run(ctx)
    assert "COIP-RES-002" in output.rules_triggered


def test_res_003_room_not_required():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["appointment_type"]["required_room_type"] = None
    output = ResourceAllocationAgent().run(ctx)
    assert output.classification == "Not Required"
    assert "COIP-RES-003" in output.rules_triggered


def test_res_005_room_config_missing_resource_conflict():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["rooms"] = []
    output = ResourceAllocationAgent().run(ctx)
    assert output.classification == "Needs Review"
    assert "COIP-RES-005" in output.rules_triggered


# --- Attendance and Follow-up Agent (COIP-AFU-001 to 005) ---------------------

def test_afu_001_confirmation_required_within_48_hours():
    ctx = deep_copy(BASE_CONTEXT)
    from datetime import date
    ctx["appointment_request"]["preferred_date"] = date.today().isoformat()
    ctx["appointment_request"]["confirmation_status"] = "pending"
    output = AttendanceAndFollowUpAgent().run(ctx)
    assert output.recommendation == "confirm_before_visit"
    assert "COIP-AFU-001" in output.rules_triggered


def test_afu_002_repeated_missed_appointments_does_not_deny_care():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["attendance_summary"] = {"total_records": 3, "attended_count": 1, "missed_count": 2}
    output = AttendanceAndFollowUpAgent().run(ctx)
    assert output.classification == "repeated_missed_appointments"
    assert "COIP-AFU-002" in output.rules_triggered
    assert output.recommendation != "deny"
    assert output.recommendation in ("confirmation_review", "confirm_before_visit")


def test_afu_003_follow_up_due():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["follow_up_summary"] = {"status": "due", "is_overdue": True}
    output = AttendanceAndFollowUpAgent().run(ctx)
    assert "COIP-AFU-003" in output.rules_triggered
    assert "FOLLOW_UP_DUE" in output.reasons


def test_afu_004_follow_up_scheduled_no_duplicate():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["follow_up_summary"] = {"status": "scheduled", "is_overdue": False}
    output = AttendanceAndFollowUpAgent().run(ctx)
    assert "COIP-AFU-004" in output.rules_triggered


def test_afu_005_insufficient_history_no_classification_guessed():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["attendance_summary"] = {}
    output = AttendanceAndFollowUpAgent().run(ctx)
    assert output.classification == "insufficient_history"
    assert "COIP-AFU-005" in output.rules_triggered


# --- Appointment Operations Decision Agent (Final Decision Precedence) -------

def _run_decision(ctx):
    req = AppointmentRequestAgent().run(deep_copy(ctx))
    sch = ScheduleAvailabilityAgent().run(deep_copy(ctx))
    que = QueueLoadAgent().run(deep_copy(ctx))
    res = ResourceAllocationAgent().run(deep_copy(ctx))
    afu = AttendanceAndFollowUpAgent().run(deep_copy(ctx))
    return AppointmentOperationsDecisionAgent().run(ctx, req, sch, que, res, afu)


def test_decision_confirm_slot():
    output = _run_decision(BASE_CONTEXT)
    assert output.classification == DECISION_CONFIRM_SLOT


def test_decision_reject_on_invalid_request():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["appointment_request"]["preferred_date"] = "2000-01-01"
    output = _run_decision(ctx)
    assert output.classification == DECISION_REJECT


def test_decision_needs_review_on_missing_queue_config():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["queue_snapshot"] = {}
    output = _run_decision(ctx)
    assert output.classification == DECISION_NEEDS_REVIEW


def test_decision_suggest_alternative_on_resource_conflict_pattern():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["existing_appointments"] = [
        {"start_time": "10:00", "status": "confirmed"},
        {"start_time": "10:00", "status": "confirmed"},
    ]
    ctx["appointment_request"]["flexibility_minutes"] = 60
    ctx["doctor_availability"].append(
        {"start_time": "14:00", "end_time": "18:00", "maximum_appointments": 2}
    )
    output = _run_decision(ctx)
    assert output.classification == DECISION_SUGGEST_ALTERNATIVE


def test_decision_await_confirmation():
    from datetime import date
    ctx = deep_copy(BASE_CONTEXT)
    ctx["appointment_request"]["preferred_date"] = date.today().isoformat()
    ctx["appointment_request"]["confirmation_status"] = "pending"
    output = _run_decision(ctx)
    assert output.classification == DECISION_AWAIT_CONFIRMATION


def test_decision_queue_over_capacity_blocks_confirm():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["queue_snapshot"] = {"booked_count": 10, "waiting_count": 2, "operational_capacity": 10}
    output = _run_decision(ctx)
    assert output.classification != DECISION_CONFIRM_SLOT


def test_decision_follow_up_due_surfaced_without_changing_decision():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["follow_up_summary"] = {"status": "due", "is_overdue": True}
    output = _run_decision(ctx)
    assert output.classification == DECISION_CONFIRM_SLOT
    assert "FOLLOW_UP_DUE" in output.reasons


# --- Safety: no clinical language anywhere in any agent's output -------------

CLINICAL_TERMS = [
    "diagnosis", "symptom", "treatment", "prescription", "triage",
    "clinical risk", "medical risk", "medication", "disease",
]


def test_no_clinical_outputs_across_all_agents():
    ctx = deep_copy(BASE_CONTEXT)
    ctx["attendance_summary"] = {"total_records": 3, "attended_count": 1, "missed_count": 2}
    ctx["follow_up_summary"] = {"status": "due", "is_overdue": True}
    outputs = [
        AppointmentRequestAgent().run(deep_copy(ctx)),
        ScheduleAvailabilityAgent().run(deep_copy(ctx)),
        QueueLoadAgent().run(deep_copy(ctx)),
        ResourceAllocationAgent().run(deep_copy(ctx)),
        AttendanceAndFollowUpAgent().run(deep_copy(ctx)),
    ]
    combined_text = json.dumps([o.model_dump() for o in outputs]).lower()
    for term in CLINICAL_TERMS:
        assert term not in combined_text, f"Clinical term '{term}' leaked into agent output"
    # Never use "risk" language for the attendance agent specifically.
    attendance_output = outputs[4]
    assert "risk" not in json.dumps(attendance_output.model_dump()).lower()
