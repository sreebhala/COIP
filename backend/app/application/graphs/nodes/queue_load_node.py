"""
Queue Load Node — Stage 3 (LangGraph Stateless).

Thin wrapper around the existing, unmodified QueueLoadAgent.
"""
from app.application.graphs.nodes._common import run_evidence_agent_node
from app.application.graphs.workflow_state import COIPGraphState
from app.services.agents.queue_load_agent import QueueLoadAgent


def queue_load_node(state: COIPGraphState) -> COIPGraphState:
    return run_evidence_agent_node(state, QueueLoadAgent, "queue")
