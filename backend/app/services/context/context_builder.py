"""
COIP Context Builder — Post #1.3.

Assembles the run-scoped SharedWorkflowContext for one appointment review.
This is data-gathering only: it retrieves reference and operational records
and records explicit missing-data flags. It does not decide, score, rank,
or recommend anything — that is reserved for the deterministic agents in
Post #1.4 and the decision agent in Post #1.5.

Hard safety rule: if the appointment request has
emergency_flag_entered_by_staff = True, this builder stops immediately and
raises EmergencyRoutingRequiredError before touching any other table. No
schedule, queue, resource, or attendance data is gathered in that case.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import (
    Appointment,
    AppointmentRequest,
    AppointmentType,
    AttendanceRecord,
    Clinic,
    ClinicLocation,
    Doctor,
    DoctorAvailability,
    FollowUpRecord,
    Patient,
    QueueSnapshot,
    Room,
)
from app.services.context.base import SharedWorkflowContext
from app.services.context.exceptions import (
    AppointmentRequestNotFoundError,
    EmergencyRoutingRequiredError,
)


class ContextBuilder:
    """Builds one run-scoped SharedWorkflowContext per appointment request.

    A fresh instance of this context is built for every workflow session. It
    is never persisted as a patient's or doctor's ongoing memory — only the
    resulting WorkflowSession.context_snapshot is stored, tied to that one
    session, matching the Context and Shared Workflow Guide."""

    def __init__(self, db: Session):
        self.db = db

    def build(self, workflow_session_id: str, appointment_request_id: str) -> SharedWorkflowContext:
        request = self.db.scalar(
            select(AppointmentRequest).where(AppointmentRequest.id == appointment_request_id)
        )
        if request is None:
            # Also allow lookup by human-readable request_code (e.g. REQ-001)
            request = self.db.scalar(
                select(AppointmentRequest).where(AppointmentRequest.request_code == appointment_request_id)
            )
        if request is None:
            raise AppointmentRequestNotFoundError(appointment_request_id)

        context = SharedWorkflowContext(
            workflow_session_id=workflow_session_id,
            appointment_request_id=request.id,
        )

        # --- Hard safety stop: emergency flag -----------------------------
        # Checked first, before any other table is queried. COIP does not
        # evaluate, score, or route emergencies — it only detects the flag
        # and halts.
        if request.emergency_flag_entered_by_staff:
            context.routing_status = "emergency_stop"
            context.appointment_request = self._request_snapshot(request)
            raise EmergencyRoutingRequiredError(appointment_request_id)

        context.appointment_request = self._request_snapshot(request)

        # --- Minimal patient snapshot --------------------------------------
        # Deliberately minimal: only the operational identity fields needed
        # to run/display a review. No contact info, no clinical data.
        patient = self.db.get(Patient, request.patient_id)
        if patient:
            context.patient_profile = {
                "patient_code": patient.patient_code,
                "full_name": patient.full_name,
                "active": patient.active,
            }
        else:
            context.missing_data_flags.append("patient_not_found")

        # --- Clinic / location ----------------------------------------------
        location = self.db.get(ClinicLocation, request.location_id)
        if location:
            context.location = {
                "location_code": location.location_code,
                "name": location.name,
                "opening_time": location.opening_time,
                "closing_time": location.closing_time,
                "active": location.active,
            }
            clinic = self.db.get(Clinic, location.clinic_id)
            if clinic:
                context.clinic = {
                    "clinic_code": clinic.clinic_code,
                    "name": clinic.name,
                    "active": clinic.active,
                }
            else:
                context.missing_data_flags.append("clinic_not_found")
        else:
            context.missing_data_flags.append("location_not_found")

        # --- Appointment type -------------------------------------------------
        appointment_type = self.db.get(AppointmentType, request.appointment_type_id)
        if appointment_type:
            context.appointment_type = {
                "type_code": appointment_type.type_code,
                "name": appointment_type.name,
                "default_duration_minutes": appointment_type.default_duration_minutes,
                "required_room_type": appointment_type.required_room_type,
                "operational_buffer_minutes": appointment_type.operational_buffer_minutes,
                "active": appointment_type.active,
            }
        else:
            context.missing_data_flags.append("appointment_type_not_found")

        # --- Requested doctor + alternatives -----------------------------------
        requested_doctor = None
        if request.requested_doctor_id:
            requested_doctor = self.db.get(Doctor, request.requested_doctor_id)
            if requested_doctor:
                context.requested_doctor = {
                    "doctor_code": requested_doctor.doctor_code,
                    "full_name": requested_doctor.full_name,
                    "specialty_label": requested_doctor.specialty_label,
                    "active": requested_doctor.active,
                }
            else:
                context.missing_data_flags.append("requested_doctor_not_found")
        else:
            context.missing_data_flags.append("no_requested_doctor_specified")

        if requested_doctor:
            alt_doctors = self.db.scalars(
                select(Doctor).where(
                    Doctor.specialty_label == requested_doctor.specialty_label,
                    Doctor.id != requested_doctor.id,
                    Doctor.active.is_(True),
                )
            ).all()
            context.alternative_doctors = [
                {
                    "doctor_code": d.doctor_code,
                    "full_name": d.full_name,
                    "specialty_label": d.specialty_label,
                }
                for d in alt_doctors
                if location and location.id in (d.location_ids or [])
            ]

        # --- Doctor availability (exact requested date) -----------------------
        if requested_doctor and location:
            availability_rows = self.db.scalars(
                select(DoctorAvailability).where(
                    DoctorAvailability.doctor_id == requested_doctor.id,
                    DoctorAvailability.location_id == location.id,
                    DoctorAvailability.availability_date == request.preferred_date,
                    DoctorAvailability.active.is_(True),
                )
            ).all()
            context.doctor_availability = [
                {
                    "start_time": row.start_time,
                    "end_time": row.end_time,
                    "slot_duration_minutes": row.slot_duration_minutes,
                    "maximum_appointments": row.maximum_appointments,
                }
                for row in availability_rows
            ]
            if not availability_rows:
                context.missing_data_flags.append("no_doctor_availability_configured")

        # --- Existing appointments (same doctor + date, for overlap awareness) --
        if requested_doctor:
            existing = self.db.scalars(
                select(Appointment).where(
                    Appointment.doctor_id == requested_doctor.id,
                    Appointment.appointment_date == request.preferred_date,
                )
            ).all()
            context.existing_appointments = [
                {
                    "appointment_code": a.appointment_code,
                    "start_time": a.start_time,
                    "end_time": a.end_time,
                    "status": a.status,
                }
                for a in existing
            ]

        # --- Queue snapshot (closest match: location + date + slot_time) -------
        queue_row = self.db.scalar(
            select(QueueSnapshot).where(
                QueueSnapshot.location_id == request.location_id,
                QueueSnapshot.snapshot_date == request.preferred_date,
                QueueSnapshot.slot_time == request.preferred_time,
            )
        )
        if queue_row:
            context.queue_snapshot = {
                "booked_count": queue_row.booked_count,
                "checked_in_count": queue_row.checked_in_count,
                "waiting_count": queue_row.waiting_count,
                "delayed_count": queue_row.delayed_count,
                "operational_capacity": queue_row.operational_capacity,
            }
        else:
            context.missing_data_flags.append("no_queue_snapshot_for_requested_slot")

        # --- Rooms matching the required room type ------------------------------
        if location and appointment_type and appointment_type.required_room_type:
            room_rows = self.db.scalars(
                select(Room).where(
                    Room.location_id == location.id,
                    Room.room_type == appointment_type.required_room_type,
                    Room.active.is_(True),
                )
            ).all()
            context.rooms = [
                {"room_code": r.room_code, "room_type": r.room_type} for r in room_rows
            ]
            if not room_rows:
                context.missing_data_flags.append("no_rooms_configured_for_required_type")

        # --- Attendance summary (operational counts only, never interpreted) ----
        attendance_rows = self.db.scalars(
            select(AttendanceRecord).where(AttendanceRecord.patient_id == request.patient_id)
        ).all()
        if attendance_rows:
            attended = sum(1 for r in attendance_rows if r.attendance_status == "attended")
            missed = sum(1 for r in attendance_rows if r.attendance_status == "missed")
            context.attendance_summary = {
                "total_records": len(attendance_rows),
                "attended_count": attended,
                "missed_count": missed,
            }
        else:
            context.missing_data_flags.append("no_attendance_history_available")

        # --- Follow-up summary -----------------------------------------------------
        follow_up = self.db.scalar(
            select(FollowUpRecord)
            .where(FollowUpRecord.patient_id == request.patient_id)
            .order_by(FollowUpRecord.due_date.desc())
        )
        if follow_up:
            context.follow_up_summary = {
                "due_date": follow_up.due_date.isoformat(),
                "status": follow_up.status,
                "is_overdue": follow_up.due_date < date.today() and follow_up.status == "due",
            }
        else:
            context.missing_data_flags.append("no_follow_up_record_found")

        # --- Final routing status ---------------------------------------------------
        # Not every flag blocks readiness. A new patient with no prior
        # attendance/follow-up history, or no queue snapshot yet recorded for
        # a slot, is a normal operational state, not a configuration gap.
        # Only missing *reference/configuration* data — the kind that means
        # the context genuinely cannot be evaluated — should downgrade
        # routing_status. All flags are still recorded either way, for full
        # transparency to a reviewer.
        hard_configuration_flags = {
            "location_not_found",
            "clinic_not_found",
            "appointment_type_not_found",
            "requested_doctor_not_found",
            "no_requested_doctor_specified",
            "no_doctor_availability_configured",
            "no_rooms_configured_for_required_type",
        }
        if any(flag in hard_configuration_flags for flag in context.missing_data_flags):
            context.routing_status = "missing_configuration"
        else:
            context.routing_status = "context_ready"
        return context

    @staticmethod
    def _request_snapshot(request: AppointmentRequest) -> dict:
        return {
            "request_code": request.request_code,
            "preferred_date": request.preferred_date.isoformat(),
            "preferred_time": request.preferred_time,
            "flexibility_minutes": request.flexibility_minutes,
            "contact_channel": request.contact_channel,
            "confirmation_status": request.confirmation_status,
            "request_source": request.request_source,
            "status": request.status,
            "emergency_flag_entered_by_staff": request.emergency_flag_entered_by_staff,
        }
