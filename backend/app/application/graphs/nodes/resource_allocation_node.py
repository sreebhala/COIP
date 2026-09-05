"""
Resource Allocation Node — Stage 3 (LangGraph Stateless).

Thin wrapper around the existing, unmodified ResourceAllocationAgent.
"""
from app.application.graphs.nodes._common import run_evidence_agent_node
from app.application.graphs.workflow_state import COIPGraphState
from app.services.agents.resource_allocation_agent import ResourceAllocationAgent


def resource_allocation_node(state: COIPGraphState) -> COIPGraphState:
    return run_evidence_agent_node(state, ResourceAllocationAgent, "resource")
