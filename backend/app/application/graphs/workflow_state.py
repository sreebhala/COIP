"""
COIP Graph State Schema — Stage 3 (LangGraph Stateless) + Stage 3.1
(Conditional LangGraph Routing).

Stage 3.1 additions: route_flags, route_decisions, selected_route,
route_reason, executed_path, skipped_agents. These are additive to the
Stage 3 schema — nothing existing was removed or renamed, so the Stage 3
graph endpoint's response shape is preserved.
"""
from typing import Any, Dict, List, Optional, TypedDict


class COIPGraphState(TypedDict, total=False):
    workflow_id: str
    domain_input: Dict[str, Any]
    shared_context: Dict[str, Any]
    routing_status: str
    agent_outputs: Dict[str, Any]
    final_recommendation: Dict[str, Any]
    explanation: str
    audit_reference: Optional[str]
    errors: List[str]

    # --- Stage 3.1: Conditional LangGraph Routing ---
    route_flags: Dict[str, bool]
    route_decisions: Dict[str, Any]
    selected_route: str
    route_reason: str
    executed_path: List[str]
    skipped_agents: List[Dict[str, str]]
