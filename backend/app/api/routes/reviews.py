from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.core.database import get_db
from app.services.context.exceptions import AppointmentRequestNotFoundError
from app.services.orchestrators.appointment_review_orchestrator import AppointmentReviewOrchestrator

router = APIRouter(prefix="/api/v1/reviews", tags=["Reviews"])


class ReviewRequest(BaseModel):
    appointment_request_id: str
    review_reason: str = "appointment_review"


@router.post("/appointment")
def review_appointment(payload: ReviewRequest, db: Session = Depends(get_db)):
    orchestrator = AppointmentReviewOrchestrator(db)
    try:
        return orchestrator.run(payload.appointment_request_id, payload.review_reason)
    except AppointmentRequestNotFoundError:
        raise HTTPException(status_code=404, detail="Appointment request not found")
