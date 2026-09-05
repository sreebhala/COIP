from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import AppointmentType, Clinic, ClinicLocation, Doctor

router = APIRouter(tags=["Reference Data"])

@router.get("/api/v1/clinics")
def list_clinics(db: Session = Depends(get_db)) -> dict:
    items = list(db.scalars(select(Clinic).order_by(Clinic.clinic_code)))
    return {"items": [{"id": x.id, "clinic_code": x.clinic_code, "name": x.name, "active": x.active} for x in items], "total": len(items)}

@router.get("/api/v1/locations")
def list_locations(db: Session = Depends(get_db)) -> dict:
    items = list(db.scalars(select(ClinicLocation).order_by(ClinicLocation.location_code)))
    return {
        "items": [
            {
                "id": x.id,
                "clinic_id": x.clinic_id,
                "location_code": x.location_code,
                "name": x.name,
                "address_label": x.address_label,
                "opening_time": x.opening_time,
                "closing_time": x.closing_time,
                "active": x.active,
            }
            for x in items
        ],
        "total": len(items),
    }

@router.get("/api/v1/doctors")
def list_doctors(db: Session = Depends(get_db)) -> dict:
    items = list(db.scalars(select(Doctor).order_by(Doctor.doctor_code)))
    return {
        "items": [
            {
                "id": x.id,
                "doctor_code": x.doctor_code,
                "full_name": x.full_name,
                "specialty_label": x.specialty_label,
                "location_ids": x.location_ids,
                "active": x.active,
            }
            for x in items
        ],
        "total": len(items),
    }

@router.get("/api/v1/appointment-types")
def list_appointment_types(db: Session = Depends(get_db)) -> dict:
    items = list(db.scalars(select(AppointmentType).order_by(AppointmentType.type_code)))
    return {
        "items": [
            {
                "id": x.id,
                "type_code": x.type_code,
                "name": x.name,
                "default_duration_minutes": x.default_duration_minutes,
                "required_room_type": x.required_room_type,
                "operational_buffer_minutes": x.operational_buffer_minutes,
                "active": x.active,
            }
            for x in items
        ],
        "total": len(items),
    }
