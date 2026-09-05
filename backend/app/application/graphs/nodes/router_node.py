"""
Router Node — Stage 3.1 (Conditional LangGraph Routing).

Pure decision node: reads shared_context, computes which of the 4
grounded routes applies, and writes route metadata to state. It does not
call any agent and does not itself skip anything — the actual skip
(resource_allocation_node vs resource_skip_node) is decided by a
conditional edge in workflow_graph.py that reads route_flags written here.

Only reached when routing_status is "context_ready" or
"missing_configuration" — the emergency_stop/not_found cases are already
routed straight past this node (see workflow_graph.py's
_route_after_context), since that branch was already established in
Stage 3 and is not being re-decided here.

Grounded in real code, not the generic route template: COIP has no
priority, SLA, or compliance field, so only routes with a real trigger in
the actual schema are computed here.
"""
from app.application.graphs.workflow_state import COIPGraphState


def router_node(state: COIPGraphState) -> COIPGraphState:
    ctx = state.get("shared_context", {})
    routing_status = state.get("routing_status", "context_ready")

    appointment_type = ctx.get("appointment_type") or {}
    required_room_type = appointment_type.get("required_room_type")
    resource_not_required = not required_room_type

    route_flags = {
        "has_missing_data": routing_status == "missing_configuration",
        "requires_human_review": False,  # emergency path never reaches this node
        "resource_not_required": resource_not_required,
    }

    if routing_status == "missing_configuration":
        selected_route = "missing_configuration_review"
        route_reason = (
            "Required clinic/doctor/room configuration could not be found for this "
            "request. All agents still run (Option A) so each can surface exactly "
            "what is missing on its own evidence, keeping this route's output "
            "identical in shape to the legacy endpoint's for the same input — "
            "only the route label and reason differ."
        )
    elif resource_not_required:
        selected_route = "resource_not_required"
        route_reason = (
            "This appointment type has no required_room_type configured. "
            "ResourceAllocationAgent's output for this case is fully deterministic "
            "(\"Not Required\", rule COIP-RES-003) regardless of context, so it is "
            "skipped rather than called for no reason."
        )
    else:
        selected_route = "standard"
        route_reason = "Complete case with no exception trigger — full agent sequence executed."

    state["route_flags"] = route_flags
    state["route_decisions"] = {
        "routing_status": routing_status,
        "required_room_type": required_room_type,
    }
    state["selected_route"] = selected_route
    state["route_reason"] = route_reason
    return state
