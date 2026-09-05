"""
Shared helper for the five evidence-agent node wrappers — Stage 3.

Not a graph node itself (leading underscore). It exists only to avoid
repeating the same three lines five times: read shared_context, call one
unmodified existing DeterministicAgent, write the result back to state.
Each node file (appointment_request_node.py, schedule_availability_node.py,
etc.) is still a thin, single-purpose wrapper — this just removes the
duplication between them.
"""
from typing import Type

from app.application.graphs.workflow_state import COIPGraphState
from app.services.agents.base import DeterministicAgent


def run_evidence_agent_node(
    state: COIPGraphState,
    agent_cls: Type[DeterministicAgent],
    output_key: str,
) -> COIPGraphState:
    # Defensive guard only — normal routing already skips these nodes via
    # the conditional edge out of context_builder_node. This just makes
    # sure a node never runs against a context that was never built,
    # matching the existing ContextBuilder hard-stop behavior.
    if state.get("routing_status") in ("emergency_stop", "not_found"):
        return state

    ctx = state["shared_context"]
    output = agent_cls().run(ctx)

    agent_outputs = state.setdefault("agent_outputs", {})
    agent_outputs[output_key] = output.model_dump()
    return state
