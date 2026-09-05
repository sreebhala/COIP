"""
Resource Skip Node — Stage 3.1 (Conditional LangGraph Routing).

Only reached via the conditional edge after queue_load_node, when
route_flags["resource_not_required"] is true. Synthesizes the exact
AgentOutput that ResourceAllocationAgent.run() would deterministically
produce for this case — verified field-for-field against
resource_allocation_agent.py's own "not required_room_type" branch:

    category = "Not Required"
    rules_triggered = [rules.RES_003_ROOM_NOT_REQUIRED.rule_id]   # "COIP-RES-003"
    reason_codes = [rules.RES_003_ROOM_NOT_REQUIRED.reason_code]  # "ROOM_NOT_REQUIRED"
    recommendation = None
    evidence = {"required_room_type": required_room_type}

This is not new business logic — it is the same deterministic outcome the
agent would already return for this input, computed here to avoid an
unnecessary call rather than to produce a different result.
"""
from app.application.graphs.workflow_state import COIPGraphState
from app.schemas.common import AgentOutput

AGENT_NAME = "ResourceAllocationAgent"
RULE_ID = "COIP-RES-003"
REASON_CODE = "ROOM_NOT_REQUIRED"


def resource_skip_node(state: COIPGraphState) -> COIPGraphState:
    ctx = state.get("shared_context", {})
    appointment_type = ctx.get("appointment_type") or {}
    required_room_type = appointment_type.get("required_room_type")

    output = AgentOutput(
        agent_name=AGENT_NAME,
        workflow_session_id=ctx.get("workflow_session_id", state.get("workflow_id", "")),
        appointment_request_id=ctx.get("appointment_request_id", ""),
        classification="Not Required",
        recommendation=None,
        reasons=[REASON_CODE],
        rules_triggered=[RULE_ID],
        evidence={"required_room_type": required_room_type},
        context_updated=["resource_result"],
    )

    agent_outputs = state.setdefault("agent_outputs", {})
    agent_outputs["resource"] = output.model_dump()

    skipped_agents = state.setdefault("skipped_agents", [])
    skipped_agents.append(
        {
            "agent": AGENT_NAME,
            "reason": (
                "required_room_type is empty for this appointment type — output is "
                "fully deterministic (\"Not Required\"), so the node was skipped and "
                "its known output was used directly."
            ),
        }
    )
    return state
