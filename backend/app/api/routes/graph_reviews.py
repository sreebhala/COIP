"""
Graph Review Route — Stage 3 (LangGraph Stateless).

New endpoint only. POST /api/v1/reviews/appointment
(backend/app/api/routes/reviews.py) is untouched and remains the source
of truth; this route exists purely so the LangGraph workflow can be run
and compared against it.
"""
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.core.database import get_db
from app.services.context.exceptions import AppointmentRequestNotFoundError
from app.application.graphs.graph_runner import AppointmentReviewGraphRunner

router = APIRouter(prefix="/api/v1/graph/reviews", tags=["Graph Reviews (Stage 3)"])


class GraphReviewRequest(BaseModel):
    appointment_request_id: str
    review_reason: str = "appointment_review"


@router.post("/appointment")
def review_appointment_graph(payload: GraphReviewRequest, db: Session = Depends(get_db)):
    runner = AppointmentReviewGraphRunner(db)
    try:
        return runner.run(payload.appointment_request_id, payload.review_reason)
    except AppointmentRequestNotFoundError:
        raise HTTPException(status_code=404, detail="Appointment request not found")
