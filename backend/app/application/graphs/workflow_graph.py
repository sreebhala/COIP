"""
COIP LangGraph Builder — Stage 3 (LangGraph Stateless) + Stage 3.1
(Conditional LangGraph Routing).

Stage 3 edges (unchanged): the emergency-stop/not-found short-circuit out
of context_builder_node, and the linear evidence-agent sequence.

Stage 3.1 addition: router_node computes the route right after context is
built, and a second conditional edge — after queue_load_node — actually
skips resource_allocation_node in favor of resource_skip_node when
route_flags["resource_not_required"] is true. The missing_configuration
route is intentionally NOT a skip (Option A from the Post 5 discovery
comment): all agents still run so the graph's output stays identical in
shape to the legacy endpoint's for that case, and only the route label
differs.
"""
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.application.graphs.nodes.appointment_request_node import appointment_request_node
from app.application.graphs.nodes.attendance_follow_up_node import attendance_follow_up_node
from app.application.graphs.nodes.context_node import make_context_builder_node
from app.application.graphs.nodes.decision_node import appointment_operations_decision_node
from app.application.graphs.nodes.explanation_audit_node import make_explanation_audit_node
from app.application.graphs.nodes.queue_load_node import queue_load_node
from app.application.graphs.nodes.resource_allocation_node import resource_allocation_node
from app.application.graphs.nodes.resource_skip_node import resource_skip_node
from app.application.graphs.nodes.router_node import router_node
from app.application.graphs.nodes.schedule_availability_node import schedule_availability_node
from app.application.graphs.workflow_state import COIPGraphState


def _route_after_context(state: COIPGraphState) -> str:
    """Stage 3's original branch, unchanged: emergency-stop/not-found skip
    straight to explanation_audit_node; everything else proceeds to the
    Stage 3.1 router."""
    if state.get("routing_status") in ("emergency_stop", "not_found"):
        return "explanation_audit_node"
    return "router_node"


def _route_after_queue(state: COIPGraphState) -> str:
    """Stage 3.1's one real skip: if the appointment type has no required
    room, ResourceAllocationAgent's output is already known ("Not
    Required") — skip the call rather than reproduce it pointlessly."""
    if state.get("route_flags", {}).get("resource_not_required"):
        return "resource_skip_node"
    return "resource_allocation_node"


def build_appointment_review_graph(db: Session):
    graph = StateGraph(COIPGraphState)

    graph.add_node("context_builder_node", make_context_builder_node(db))
    graph.add_node("router_node", router_node)
    graph.add_node("appointment_request_node", appointment_request_node)
    graph.add_node("schedule_availability_node", schedule_availability_node)
    graph.add_node("queue_load_node", queue_load_node)
    graph.add_node("resource_allocation_node", resource_allocation_node)
    graph.add_node("resource_skip_node", resource_skip_node)
    graph.add_node("attendance_follow_up_node", attendance_follow_up_node)
    graph.add_node("appointment_operations_decision_node", appointment_operations_decision_node)
    graph.add_node("explanation_audit_node", make_explanation_audit_node(db))

    graph.add_edge(START, "context_builder_node")
    graph.add_conditional_edges(
        "context_builder_node",
        _route_after_context,
        {
            "explanation_audit_node": "explanation_audit_node",
            "router_node": "router_node",
        },
    )
    graph.add_edge("router_node", "appointment_request_node")
    graph.add_edge("appointment_request_node", "schedule_availability_node")
    graph.add_edge("schedule_availability_node", "queue_load_node")
    graph.add_conditional_edges(
        "queue_load_node",
        _route_after_queue,
        {
            "resource_allocation_node": "resource_allocation_node",
            "resource_skip_node": "resource_skip_node",
        },
    )
    graph.add_edge("resource_allocation_node", "attendance_follow_up_node")
    graph.add_edge("resource_skip_node", "attendance_follow_up_node")
    graph.add_edge("attendance_follow_up_node", "appointment_operations_decision_node")
    graph.add_edge("appointment_operations_decision_node", "explanation_audit_node")
    graph.add_edge("explanation_audit_node", END)

    return graph.compile()
