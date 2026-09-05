from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.core.database import get_db
from app.services import audit_service

router = APIRouter(prefix="/api/v1/audit", tags=["Audit"])


@router.get("/{audit_reference}")
def get_audit_record(audit_reference: str, db: Session = Depends(get_db)):
    record = audit_service.get_by_audit_reference(db, audit_reference)
    if not record:
        raise HTTPException(status_code=404, detail="Audit record not found")
    return {
        "audit_reference": record.audit_reference,
        "workflow_session_id": record.workflow_session_id,
        "appointment_request_id": record.appointment_request_id,
        "decision_type": "clinic_appointment_operations_review",
        "decision": record.decision_category,
        "reason_codes": record.reason_codes,
        "evidence": record.evidence_snapshot,
        "explanation": record.explanation,
        "created_at": record.created_at.isoformat(),
    }
