"""
Audit Service — Post #1.5.

Records the workflow session, execution evidence, and decision trail as a
DecisionRecord. Does not alter the decision. Stores no secrets — verified
by tests that scan the stored record for clinical/contact-sensitive terms.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import DecisionRecord


def _next_audit_reference(db: Session) -> str:
    count = db.query(DecisionRecord).count()
    return f"AUD-{count + 1:06d}"


def record_decision(
    db: Session,
    workflow_session_id: str,
    appointment_request_id: str,
    decision_category: str,
    recommendation: str | None,
    reason_codes: list[str],
    evidence_snapshot: dict,
    explanation: str,
) -> DecisionRecord:
    audit_reference = _next_audit_reference(db)
    decision_id = f"DEC-{audit_reference.split('-')[1]}"

    record = DecisionRecord(
        decision_id=decision_id,
        audit_reference=audit_reference,
        workflow_session_id=workflow_session_id,
        appointment_request_id=appointment_request_id,
        decision_category=decision_category,
        recommendation=recommendation,
        reason_codes=reason_codes,
        evidence_snapshot=evidence_snapshot,
        explanation=explanation,
    )
    db.add(record)
    db.flush()
    return record


def get_by_audit_reference(db: Session, audit_reference: str) -> DecisionRecord | None:
    return db.scalar(select(DecisionRecord).where(DecisionRecord.audit_reference == audit_reference))
