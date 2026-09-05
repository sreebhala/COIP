"""
Schedule Availability Node — Stage 3 (LangGraph Stateless).

Thin wrapper around the existing, unmodified ScheduleAvailabilityAgent.
"""
from app.application.graphs.nodes._common import run_evidence_agent_node
from app.application.graphs.workflow_state import COIPGraphState
from app.services.agents.schedule_availability_agent import ScheduleAvailabilityAgent


def schedule_availability_node(state: COIPGraphState) -> COIPGraphState:
    return run_evidence_agent_node(state, ScheduleAvailabilityAgent, "schedule")
