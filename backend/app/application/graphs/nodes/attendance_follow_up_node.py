"""
Attendance & Follow-Up Node — Stage 3 (LangGraph Stateless).

Thin wrapper around the existing, unmodified AttendanceAndFollowUpAgent.
"""
from app.application.graphs.nodes._common import run_evidence_agent_node
from app.application.graphs.workflow_state import COIPGraphState
from app.services.agents.attendance_follow_up_agent import AttendanceAndFollowUpAgent


def attendance_follow_up_node(state: COIPGraphState) -> COIPGraphState:
    return run_evidence_agent_node(state, AttendanceAndFollowUpAgent, "attendance_follow_up")
