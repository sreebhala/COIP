"""
Appointment Request Node — Stage 3 (LangGraph Stateless).

Thin wrapper around the existing, unmodified AppointmentRequestAgent.
"""
from app.application.graphs.nodes._common import run_evidence_agent_node
from app.application.graphs.workflow_state import COIPGraphState
from app.services.agents.appointment_request_agent import AppointmentRequestAgent


def appointment_request_node(state: COIPGraphState) -> COIPGraphState:
    return run_evidence_agent_node(state, AppointmentRequestAgent, "request_validation")
