"""
Context Builder Node — Stage 3 (LangGraph Stateless).

Thin wrapper: reads `domain_input`, calls the existing, unmodified
ContextBuilder, writes `shared_context` + `routing_status` back to graph
state. The emergency-stop hard-safety-rule and unknown-request handling
still live entirely in ContextBuilder / EmergencyRoutingRequiredError —
this node does not re-implement or duplicate that logic.
"""
from sqlalchemy.orm import Session

from app.application.graphs.workflow_state import COIPGraphState
from app.services.context.context_builder import ContextBuilder
from app.services.context.exceptions import (
    AppointmentRequestNotFoundError,
    EmergencyRoutingRequiredError,
)


def make_context_builder_node(db: Session):
    """Factory, not a decorator: the node needs a live db Session, which
    LangGraph node signatures (state -> state) don't carry, so it's bound
    via closure when the graph is built (see workflow_graph.py)."""

    def context_builder_node(state: COIPGraphState) -> COIPGraphState:
        builder = ContextBuilder(db)
        appointment_request_id = state["domain_input"]["appointment_request_id"]
        workflow_id = state["workflow_id"]

        try:
            context = builder.build(workflow_id, appointment_request_id)
        except AppointmentRequestNotFoundError:
            state.setdefault("errors", []).append("appointment_request_not_found")
            state["routing_status"] = "not_found"
            return state
        except EmergencyRoutingRequiredError as exc:
            state["routing_status"] = "emergency_stop"
            state["explanation"] = str(exc)
            state["shared_context"] = {
                "appointment_request_id": appointment_request_id,
                "routing_status": "emergency_stop",
            }
            return state

        state["shared_context"] = context.model_dump()
        state["routing_status"] = context.routing_status
        return state

    return context_builder_node
