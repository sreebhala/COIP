from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import AppointmentRequest, AppointmentType, ClinicLocation, Doctor, Patient
from app.schemas.appointment import AppointmentRequestCreate, AppointmentRequestListResponse, AppointmentRequestRead

router = APIRouter(prefix="/api/v1/appointment-requests", tags=["Appointment Requests"])

@router.get("", response_model=AppointmentRequestListResponse)
def list_appointment_requests(db: Session = Depends(get_db)) -> AppointmentRequestListResponse:
    items = list(db.scalars(select(AppointmentRequest).order_by(AppointmentRequest.requested_at.desc())))
    return AppointmentRequestListResponse(items=[AppointmentRequestRead.model_validate(x) for x in items], total=len(items))

@router.post("", response_model=AppointmentRequestRead, status_code=status.HTTP_201_CREATED)
def create_appointment_request(payload: AppointmentRequestCreate, db: Session = Depends(get_db)) -> AppointmentRequestRead:
    if db.scalar(select(AppointmentRequest).where(AppointmentRequest.request_code == payload.request_code)):
        raise HTTPException(status_code=409, detail="Request code already exists")
    if not db.get(Patient, payload.patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    if not db.get(ClinicLocation, payload.location_id):
        raise HTTPException(status_code=404, detail="Location not found")
    if not db.get(AppointmentType, payload.appointment_type_id):
        raise HTTPException(status_code=404, detail="Appointment type not found")
    if payload.requested_doctor_id and not db.get(Doctor, payload.requested_doctor_id):
        raise HTTPException(status_code=404, detail="Doctor not found")
    item = AppointmentRequest(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return AppointmentRequestRead.model_validate(item)

@router.get("/{request_id}", response_model=AppointmentRequestRead)
def get_appointment_request(request_id: str, db: Session = Depends(get_db)) -> AppointmentRequestRead:
    item = db.get(AppointmentRequest, request_id)
    if not item:
        item = db.scalar(select(AppointmentRequest).where(AppointmentRequest.request_code == request_id))
    if not item:
        raise HTTPException(status_code=404, detail="Appointment request not found")
    return AppointmentRequestRead.model_validate(item)
