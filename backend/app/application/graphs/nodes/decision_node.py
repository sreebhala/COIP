"""
Appointment Operations Decision Node — Stage 3 (LangGraph Stateless).

Thin wrapper around the existing, unmodified
AppointmentOperationsDecisionAgent — the only agent authorized to produce
the final decision. Reconstructs the five upstream AgentOutput objects
from graph state (they were stored as plain dicts so state stays JSON-
serializable) and calls the decision agent with the exact same signature
the deterministic orchestrator already uses. No decision logic is
duplicated or altered here.
"""
from app.application.graphs.workflow_state import COIPGraphState
from app.schemas.common import AgentOutput
from app.services.agents.appointment_operations_decision_agent import AppointmentOperationsDecisionAgent


def appointment_operations_decision_node(state: COIPGraphState) -> COIPGraphState:
    if state.get("routing_status") in ("emergency_stop", "not_found"):
        return state

    ctx = state["shared_context"]
    outputs = state.get("agent_outputs", {})

    req_output = AgentOutput(**outputs["request_validation"])
    sch_output = AgentOutput(**outputs["schedule"])
    que_output = AgentOutput(**outputs["queue"])
    res_output = AgentOutput(**outputs["resource"])
    afu_output = AgentOutput(**outputs["attendance_follow_up"])

    decision_output = AppointmentOperationsDecisionAgent().run(
        ctx, req_output, sch_output, que_output, res_output, afu_output
    )

    outputs["decision"] = decision_output.model_dump()
    state["agent_outputs"] = outputs
    state["final_recommendation"] = decision_output.model_dump()
    return state
