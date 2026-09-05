"""
Explanation & Audit Node — Stage 3 (LangGraph Stateless) + Stage 3.1
(Conditional LangGraph Routing).

Thin wrapper around the existing, unmodified explanation_service and
audit_service. Handles both the normal completion path and the
emergency-stop/not-found paths, matching exactly what the deterministic
orchestrator already does: no audit record is created for an
emergency-stopped or unknown request — same as Stage 3.

Stage 3.1 addition: when an audit record IS created, the route decision
(selected_route, route_reason, route_flags) is now included in
evidence_snapshot under an additive "routing" key, so it is retrievable
from GET /api/v1/audit/{audit_reference} — satisfying "Record route
decision in audit if audit exists" without changing the shape of any
existing evidence_snapshot key.
"""
from sqlalchemy.orm import Session

from app.application.graphs.workflow_state import COIPGraphState
from app.schemas.common import AgentOutput
from app.services import audit_service
from app.services.explanation_service import build_explanation


def make_explanation_audit_node(db: Session):
    def explanation_audit_node(state: COIPGraphState) -> COIPGraphState:
        if state.get("routing_status") in ("emergency_stop", "not_found"):
            # Emergency case: explanation was already set by
            # context_builder_node to the EmergencyRoutingRequiredError
            # message. Not-found case: handled entirely by graph_runner
            # re-raising AppointmentRequestNotFoundError -> HTTP 404.
            return state

        outputs = state.get("agent_outputs", {})
        req_output = AgentOutput(**outputs["request_validation"])
        sch_output = AgentOutput(**outputs["schedule"])
        que_output = AgentOutput(**outputs["queue"])
        res_output = AgentOutput(**outputs["resource"])
        afu_output = AgentOutput(**outputs["attendance_follow_up"])
        decision_output = AgentOutput(**outputs["decision"])

        explanation = build_explanation(
            decision_output.classification, sch_output, que_output, res_output, afu_output
        )
        state["explanation"] = explanation

        all_reason_codes = list(dict.fromkeys(decision_output.reasons))

        evidence_snapshot = {
            "request_validation": req_output.evidence,
            "schedule": sch_output.evidence,
            "queue": que_output.evidence,
            "resource": res_output.evidence,
            "attendance_follow_up": afu_output.evidence,
            # Stage 3.1: additive routing info, does not change any
            # existing evidence_snapshot key.
            "routing": {
                "selected_route": state.get("selected_route", "standard"),
                "route_reason": state.get("route_reason", ""),
                "route_flags": state.get("route_flags", {}),
            },
        }

        decision_record = audit_service.record_decision(
            db,
            workflow_session_id=state["workflow_id"],
            appointment_request_id=state["domain_input"]["appointment_request_id"],
            decision_category=decision_output.classification,
            recommendation=decision_output.recommendation,
            reason_codes=all_reason_codes,
            evidence_snapshot=evidence_snapshot,
            explanation=explanation,
        )

        state["audit_reference"] = decision_record.audit_reference
        state["final_recommendation"] = {
            **state.get("final_recommendation", {}),
            "reason_codes": all_reason_codes,
        }
        return state

    return explanation_audit_node
