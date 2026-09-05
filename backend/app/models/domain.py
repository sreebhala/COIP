from __future__ import annotations
from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

def new_id() -> str:
    return str(uuid4())

class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    clinic_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    locations: Mapped[list["ClinicLocation"]] = relationship(back_populates="clinic", cascade="all, delete-orphan")

class ClinicLocation(Base):
    __tablename__ = "clinic_locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), index=True)
    location_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    address_label: Mapped[str] = mapped_column(String(200))
    opening_time: Mapped[str] = mapped_column(String(5))
    closing_time: Mapped[str] = mapped_column(String(5))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    clinic: Mapped["Clinic"] = relationship(back_populates="locations")
    rooms: Mapped[list["Room"]] = relationship(back_populates="location", cascade="all, delete-orphan")

class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    patient_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    doctor_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    specialty_label: Mapped[str] = mapped_column(String(120))
    location_ids: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class AppointmentType(Base):
    __tablename__ = "appointment_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    type_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    default_duration_minutes: Mapped[int] = mapped_column(Integer, default=20)
    required_room_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    operational_buffer_minutes: Mapped[int] = mapped_column(Integer, default=5)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    doctor_id: Mapped[str] = mapped_column(ForeignKey("doctors.id"), index=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("clinic_locations.id"), index=True)
    availability_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[str] = mapped_column(String(5))
    end_time: Mapped[str] = mapped_column(String(5))
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, default=20)
    maximum_appointments: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    location_id: Mapped[str] = mapped_column(ForeignKey("clinic_locations.id"), index=True)
    room_code: Mapped[str] = mapped_column(String(30), index=True)
    room_type: Mapped[str] = mapped_column(String(60))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    location: Mapped["ClinicLocation"] = relationship(back_populates="rooms")

class AppointmentRequest(Base):
    __tablename__ = "appointment_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    request_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("clinic_locations.id"), index=True)
    requested_doctor_id: Mapped[str | None] = mapped_column(ForeignKey("doctors.id"), nullable=True, index=True)
    appointment_type_id: Mapped[str] = mapped_column(ForeignKey("appointment_types.id"), index=True)
    preferred_date: Mapped[date] = mapped_column(Date)
    preferred_time: Mapped[str] = mapped_column(String(5))
    flexibility_minutes: Mapped[int] = mapped_column(Integer, default=0)
    contact_channel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    confirmation_status: Mapped[str] = mapped_column(String(30), default="pending")
    request_source: Mapped[str] = mapped_column(String(40), default="phone")
    status: Mapped[str] = mapped_column(String(30), default="pending")
    emergency_flag_entered_by_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    appointment_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    request_id: Mapped[str | None] = mapped_column(ForeignKey("appointment_requests.id"), nullable=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[str] = mapped_column(ForeignKey("doctors.id"), index=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("clinic_locations.id"), index=True)
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)
    appointment_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[str] = mapped_column(String(5))
    end_time: Mapped[str] = mapped_column(String(5))
    status: Mapped[str] = mapped_column(String(30), default="confirmed")

class QueueSnapshot(Base):
    __tablename__ = "queue_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    location_id: Mapped[str] = mapped_column(ForeignKey("clinic_locations.id"), index=True)
    doctor_id: Mapped[str | None] = mapped_column(ForeignKey("doctors.id"), nullable=True, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date)
    slot_time: Mapped[str] = mapped_column(String(5))
    booked_count: Mapped[int] = mapped_column(Integer, default=0)
    checked_in_count: Mapped[int] = mapped_column(Integer, default=0)
    waiting_count: Mapped[int] = mapped_column(Integer, default=0)
    delayed_count: Mapped[int] = mapped_column(Integer, default=0)
    operational_capacity: Mapped[int] = mapped_column(Integer, default=1)

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    appointment_date: Mapped[date] = mapped_column(Date)
    attendance_status: Mapped[str] = mapped_column(String(30))
    confirmation_status: Mapped[str] = mapped_column(String(30))
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class FollowUpRecord(Base):
    __tablename__ = "follow_up_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    due_date: Mapped[date] = mapped_column(Date)
    appointment_type_id: Mapped[str] = mapped_column(ForeignKey("appointment_types.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="due")
    source_reference: Mapped[str | None] = mapped_column(String(60), nullable=True)

class WorkflowSession(Base):
    __tablename__ = "workflow_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workflow_session_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    appointment_request_id: Mapped[str] = mapped_column(String(36), index=True)
    review_reason: Mapped[str] = mapped_column(String(60), default="appointment_review")
    status: Mapped[str] = mapped_column(String(30), default="created")
    input_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    context_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    final_output_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class AgentExecutionLog(Base):
    __tablename__ = "agent_execution_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workflow_session_id: Mapped[str] = mapped_column(String(40), index=True)
    agent_name: Mapped[str] = mapped_column(String(100))
    sequence_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30))
    input_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    output_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    rules_triggered: Mapped[list] = mapped_column(JSON, default=list)
    context_updated: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)

class DecisionRecord(Base):
    __tablename__ = "decision_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    decision_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    audit_reference: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    workflow_session_id: Mapped[str] = mapped_column(String(40), index=True)
    appointment_request_id: Mapped[str] = mapped_column(String(36), index=True)
    decision_category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    evidence_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
