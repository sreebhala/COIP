from datetime import date, datetime, timedelta
import contextlib
import json
from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
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

DATA = json.loads(
    '{"clinic": {"clinic_code": "CLN-001", "name": "Riverside Clinic Demo", "active": true}, "locations": [{"location_code": "LOC-001",'
    ' "name": "Riverside Central", "address_label": "Central Demo Location", "opening_time": "08:00",'
    ' "closing_time": "20:00", "active": true}, {"location_code": "LOC-002", "name": "Riverside North",'
    ' "address_label": "North Demo Location", "opening_time": "09:00", "closing_time": "18:00",'
    ' "active": true}], "doctors": [{"doctor_code": "DOC-001", "full_name": "Dr. Ananya Demo", "specialty_label": "General Consultation",'
    ' "active": true}, {"doctor_code": "DOC-002", "full_name": "Dr. Rahul Demo", "specialty_label": "Scheduled Follow-up",'
    ' "active": true}, {"doctor_code": "DOC-003", "full_name": "Dr. Nisha Demo", "specialty_label": "General Consultation",'
    ' "active": false}], "appointment_types": [{"type_code": "APT-NEW", "name": "New Consultation",'
    ' "default_duration_minutes": 20, "required_room_type": "consultation", "operational_buffer_minutes": 5,'
    ' "active": true}, {"type_code": "APT-FUP", "name": "Scheduled Follow-up", "default_duration_minutes": 15,'
    ' "required_room_type": "consultation", "operational_buffer_minutes": 5, "active": true}, {"type_code": "APT-PRO",'
    ' "name": "Configured Procedure Slot", "default_duration_minutes": 30, "required_room_type": "procedure",'
    ' "operational_buffer_minutes": 10, "active": true}, {"type_code": "APT-TELE", "name": "Teleconsultation",'
    ' "default_duration_minutes": 15, "required_room_type": null, "operational_buffer_minutes": 5,'
    ' "active": true}]}'
)

def seed(db_session=None) -> None:
    """Populate demo/reference data.

    Defaults to the real application database (used by `python -m
    app.data.seed` and by the running app). Tests must never rely on this
    default — pass an explicit db_session bound to a separate test engine
    instead (see tests/conftest.py), so running the test suite never
    touches or wipes the real dev/demo database. (Post #1.4 fix, applied
    per mentor direction after the Post #1.3 review.)
    """
    if db_session is None:
        Base.metadata.create_all(bind=engine)
        session_ctx = SessionLocal()
    else:
        Base.metadata.create_all(bind=db_session.get_bind())
        session_ctx = contextlib.nullcontext(db_session)
    with session_ctx as db:
        # Post #1.6 fix: seed dates are computed relative to "today" so the
        # demo scenarios (Confirm Slot, Alternative Slot, Await Confirmation,
        # etc.) remain demonstrable in the UI regardless of when this is run
        # — rather than using fixed calendar dates that inevitably go stale.
        # See COIP_README.md "Known Limitations" for the history of this fix.
        today = date.today()
        DAY1 = (today + timedelta(days=1)).isoformat()
        DAY2 = (today + timedelta(days=2)).isoformat()
        HIST_1 = (today - timedelta(days=90)).isoformat()
        HIST_2 = (today - timedelta(days=60)).isoformat()
        HIST_3 = (today - timedelta(days=30)).isoformat()
        FOLLOW_UP_DUE = (today - timedelta(days=1)).isoformat()
        REQUESTED_AT = datetime.combine(today - timedelta(days=4), datetime.min.time()).isoformat()

        clinic = db.scalar(select(Clinic).where(Clinic.clinic_code == "CLN-001"))
        if not clinic:
            clinic = Clinic(**DATA["clinic"])
            db.add(clinic)
            db.flush()

        locations = {}
        for item in DATA["locations"]:
            location = db.scalar(select(ClinicLocation).where(ClinicLocation.location_code == item["location_code"]))
            if not location:
                location = ClinicLocation(clinic_id=clinic.id, **item)
                db.add(location)
                db.flush()
            locations[item["location_code"]] = location

        doctors = {}
        for item in DATA["doctors"]:
            doctor = db.scalar(select(Doctor).where(Doctor.doctor_code == item["doctor_code"]))
            if not doctor:
                doctor = Doctor(location_ids=[locations["LOC-001"].id, locations["LOC-002"].id], **item)
                db.add(doctor)
                db.flush()
            doctors[item["doctor_code"]] = doctor

        types = {}
        for item in DATA["appointment_types"]:
            appointment_type = db.scalar(select(AppointmentType).where(AppointmentType.type_code == item["type_code"]))
            if not appointment_type:
                appointment_type = AppointmentType(**item)
                db.add(appointment_type)
                db.flush()
            types[item["type_code"]] = appointment_type

        for location_code, room_rows in {
            "LOC-001": [("ROOM-01", "consultation"), ("ROOM-02", "consultation"), ("ROOM-03", "procedure")],
            "LOC-002": [("ROOM-N1", "consultation"), ("ROOM-N2", "procedure")],
        }.items():
            location = locations[location_code]
            for room_code, room_type in room_rows:
                if not db.scalar(select(Room).where(Room.location_id == location.id, Room.room_code == room_code)):
                    db.add(Room(location_id=location.id, room_code=room_code, room_type=room_type, active=True))

        for doctor_code, location_code, day, start, end, capacity in [
            ("DOC-001", "LOC-001", DAY1, "09:00", "13:00", 10),
            ("DOC-001", "LOC-001", DAY1, "14:00", "18:00", 10),
            ("DOC-002", "LOC-001", DAY1, "10:00", "16:00", 16),
            ("DOC-002", "LOC-002", DAY2, "09:00", "14:00", 12),
        ]:
            exists = db.scalar(
                select(DoctorAvailability).where(
                    DoctorAvailability.doctor_id == doctors[doctor_code].id,
                    DoctorAvailability.location_id == locations[location_code].id,
                    DoctorAvailability.availability_date == date.fromisoformat(day),
                    DoctorAvailability.start_time == start,
                )
            )
            if not exists:
                db.add(
                    DoctorAvailability(
                        doctor_id=doctors[doctor_code].id,
                        location_id=locations[location_code].id,
                        availability_date=date.fromisoformat(day),
                        start_time=start,
                        end_time=end,
                        slot_duration_minutes=20,
                        maximum_appointments=capacity,
                        active=True,
                    )
                )

        patients = {}
        for code, name, email, phone in [
            ("PAT-001", "Aarav Demo", "aarav@example.test", "0000003001"),
            ("PAT-002", "Diya Demo", "diya@example.test", "0000003002"),
            ("PAT-003", "Kabir Demo", "kabir@example.test", "0000003003"),
            ("PAT-004", "Meera Demo", "meera@example.test", "0000003004"),
            ("PAT-005", "Rohan Demo", "rohan@example.test", "0000003005"),
            ("PAT-006", "Vikram Demo", "vikram@example.test", "0000003006"),
            ("PAT-007", "Sana Demo", "sana@example.test", "0000003007"),
        ]:
            patient = db.scalar(select(Patient).where(Patient.patient_code == code))
            if not patient:
                patient = Patient(patient_code=code, full_name=name, email=email, phone=phone, active=True)
                db.add(patient)
                db.flush()
            patients[code] = patient

        requests = [
            ("REQ-001", "PAT-001", "LOC-001", "DOC-001", "APT-NEW", DAY1, "10:00", 0, "phone", "confirmed", False),
            ("REQ-002", "PAT-002", "LOC-001", "DOC-001", "APT-NEW", DAY1, "11:00", 60, "email", "pending", False),
            ("REQ-003", "PAT-003", "LOC-001", "DOC-002", "APT-PRO", DAY1, "12:00", 60, "phone", "confirmed", False),
            ("REQ-004", "PAT-004", "LOC-001", "DOC-002", "APT-FUP", DAY1, "14:00", 30, "phone", "pending", False),
            ("REQ-005", "PAT-005", "LOC-002", "DOC-002", "APT-FUP", DAY2, "10:00", 30, "phone", "pending", True),
            # Stage 3.1 addition: DOC-003 has zero seeded DoctorAvailability
            # rows -> ContextBuilder sets routing_status="missing_configuration".
            # Exercises the missing-configuration conditional route.
            ("REQ-006", "PAT-006", "LOC-001", "DOC-003", "APT-NEW", DAY1, "09:00", 0, "phone", "pending", False),
            # Stage 3.1 addition: APT-TELE has required_room_type=None ->
            # ResourceAllocationAgent deterministically returns "Not
            # Required". Exercises the resource-not-required conditional
            # route. DOC-001 has seeded availability 09:00-13:00 on DAY1.
            ("REQ-007", "PAT-007", "LOC-001", "DOC-001", "APT-TELE", DAY1, "09:30", 0, "phone", "pending", False),
        ]
        for code, patient_code, location_code, doctor_code, type_code, day, time_value, flexibility, channel, confirmation, emergency in requests:
            if not db.scalar(select(AppointmentRequest).where(AppointmentRequest.request_code == code)):
                db.add(
                    AppointmentRequest(
                        request_code=code,
                        patient_id=patients[patient_code].id,
                        location_id=locations[location_code].id,
                        requested_doctor_id=doctors[doctor_code].id,
                        appointment_type_id=types[type_code].id,
                        preferred_date=date.fromisoformat(day),
                        preferred_time=time_value,
                        flexibility_minutes=flexibility,
                        contact_channel=channel,
                        confirmation_status=confirmation,
                        request_source="demo",
                        status="pending",
                        emergency_flag_entered_by_staff=emergency,
                        requested_at=datetime.fromisoformat(REQUESTED_AT),
                    )
                )

        if not db.scalar(select(QueueSnapshot).where(QueueSnapshot.location_id == locations["LOC-001"].id, QueueSnapshot.slot_time == "10:00")):
            db.add(
                QueueSnapshot(
                    location_id=locations["LOC-001"].id,
                    doctor_id=doctors["DOC-001"].id,
                    snapshot_date=date.fromisoformat(DAY1),
                    slot_time="10:00",
                    booked_count=6,
                    checked_in_count=0,
                    waiting_count=0,
                    delayed_count=0,
                    operational_capacity=10,
                )
            )

        # Post #1.6 addition: two more queue snapshots so Busy and Over
        # Capacity queue states (Scenario 3) are demonstrable live in the
        # UI, not only via automated tests.
        if not db.scalar(select(QueueSnapshot).where(QueueSnapshot.location_id == locations["LOC-001"].id, QueueSnapshot.slot_time == "11:00")):
            db.add(
                QueueSnapshot(
                    location_id=locations["LOC-001"].id,
                    doctor_id=doctors["DOC-001"].id,
                    snapshot_date=date.fromisoformat(DAY1),
                    slot_time="11:00",
                    booked_count=8,
                    checked_in_count=0,
                    waiting_count=0,
                    delayed_count=0,
                    operational_capacity=10,
                )
            )
        if not db.scalar(select(QueueSnapshot).where(QueueSnapshot.location_id == locations["LOC-001"].id, QueueSnapshot.slot_time == "12:00")):
            db.add(
                QueueSnapshot(
                    location_id=locations["LOC-001"].id,
                    doctor_id=doctors["DOC-002"].id,
                    snapshot_date=date.fromisoformat(DAY1),
                    slot_time="12:00",
                    booked_count=10,
                    checked_in_count=0,
                    waiting_count=2,
                    delayed_count=0,
                    operational_capacity=10,
                )
            )

        for status_value, day in [("missed", HIST_1), ("missed", HIST_2), ("attended", HIST_3)]:
            exists = db.scalar(select(AttendanceRecord).where(AttendanceRecord.patient_id == patients["PAT-004"].id, AttendanceRecord.appointment_date == date.fromisoformat(day)))
            if not exists:
                db.add(
                    AttendanceRecord(
                        patient_id=patients["PAT-004"].id,
                        appointment_date=date.fromisoformat(day),
                        attendance_status=status_value,
                        confirmation_status="confirmed",
                    )
                )

        if not db.scalar(select(FollowUpRecord).where(FollowUpRecord.patient_id == patients["PAT-004"].id)):
            db.add(
                FollowUpRecord(
                    patient_id=patients["PAT-004"].id,
                    due_date=date.fromisoformat(FOLLOW_UP_DUE),
                    appointment_type_id=types["APT-FUP"].id,
                    status="due",
                    source_reference="DEMO-FUP-001",
                )
            )

        db.commit()

    print("COIP seed data loaded")

if __name__ == "__main__":
    seed()
