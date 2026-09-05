"""
Graph Runner Service — Stage 3 (LangGraph Stateless) + Stage 3.1
(Conditional LangGraph Routing).

Owns WorkflowSession bookkeeping and shapes the graph endpoint's
response. Stage 3.1 additions are purely additive to the Stage 3 response
shape — graph_mode is deliberately left as "langgraph_stateless"
(unchanged) rather than renamed to "conditional_langgraph", specifically
to avoid breaking the existing Stage 3 old-vs-graph comparison tests and
the "Do not break the Stage 3 graph endpoint" rule. A new
"conditional_routing": true field marks that routing is active on top of
the same endpoint.

executed_path and the emergency-case entries of skipped_agents are
computed here (rather than having every node append its own name) to
keep each node thin and free of bookkeeping concerns, per the "graph node
= read state -> call existing agent/service -> update state -> return
state" design principle from Post 2/5.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.application.graphs.workflow_graph import build_appointment_review_graph
from app.models.domain import WorkflowSession
from app.schemas.common import AgentOutput
from app.services.context.exceptions import AppointmentRequestNotFoundError
from app.services.orchestrators.appointment_review_orchestrator import _log_agent_run

ALL_EVIDENCE_AGENTS = [
    "AppointmentRequestAgent",
    "ScheduleAvailabilityAgent",
    "QueueLoadAgent",
    "ResourceAllocationAgent",
    "AttendanceAndFollowUpAgent",
    "AppointmentOperationsDecisionAgent",
]


def _next_workflow_session_id(db: Session) -> str:
    count = db.query(WorkflowSession).count()
    return f"WF-{count + 1:06d}"


class AppointmentReviewGraphRunner:
    def __init__(self, db: Session):
        self.db = db

    def run(self, appointment_request_id: str, review_reason: str = "appointment_review") -> dict:
        workflow_id = _next_workflow_session_id(self.db)

        session_row = WorkflowSession(
            workflow_session_id=workflow_id,
            appointment_request_id=appointment_request_id,
            review_reason=review_reason,
            status="in_progress",
            input_snapshot={"appointment_request_id": appointment_request_id},
        )
        self.db.add(session_row)
        self.db.flush()

        graph = build_appointment_review_graph(self.db)

        initial_state = {
            "workflow_id": workflow_id,
            "domain_input": {
                "appointment_request_id": appointment_request_id,
                "review_reason": review_reason,
            },
            "agent_outputs": {},
            "errors": [],
        }

        final_state = graph.invoke(initial_state)

        if "appointment_request_not_found" in final_state.get("errors", []):
            self.db.rollback()
            raise AppointmentRequestNotFoundError(appointment_request_id)

        if final_state.get("routing_status") == "emergency_stop":
            session_row.status = "emergency_stop"
            session_row.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            return {
                # Same keys as the deterministic endpoint's emergency-stop
                # response (workflow_session_id, appointment_request_id,
                # status, message), plus additive fields only.
                "workflow_id": workflow_id,
                "workflow_session_id": workflow_id,
                "graph_mode": "langgraph_stateless",
                "conditional_routing": True,
                "conditional_langgraph": True,
                "appointment_request_id": appointment_request_id,
                "status": "emergency_stop",
                "message": final_state.get("explanation", ""),
                # Stage 3.1 route fields — the emergency route is fully
                # decided by context_builder_node before router_node ever
                # runs, so it is described here rather than via state.
                "selected_route": "emergency_human_review",
                "route_reason": (
                    "Emergency flag entered by staff — automated evidence agents "
                    "bypassed for safety, routed directly for human review."
                ),
                "route_flags": {
                    "has_missing_data": False,
                    "requires_human_review": True,
                    "resource_not_required": False,
                },
                "executed_path": ["context_builder_node", "explanation_audit_node"],
                "skipped_agents": [
                    {
                        "agent": agent,
                        "reason": "Emergency flag detected — automated evidence-gathering bypassed for safety.",
                    }
                    for agent in ALL_EVIDENCE_AGENTS
                ],
            }

        outputs = final_state.get("agent_outputs", {})
        req_output = outputs.get("request_validation", {})
        sch_output = outputs.get("schedule", {})
        que_output = outputs.get("queue", {})
        res_output = outputs.get("resource", {})
        afu_output = outputs.get("attendance_follow_up", {})
        decision_output = outputs.get("decision", {})
        ctx = final_state.get("shared_context", {})

        route_flags = final_state.get("route_flags", {})
        selected_route = final_state.get("selected_route", "standard")
        route_reason = final_state.get("route_reason", "")

        # Persist each node's execution into AgentExecutionLog using the
        # exact same helper the deterministic orchestrator uses, with the
        # same sequence numbers and input_summary shape — unchanged from
        # Stage 3, still runs even when resource_allocation_node itself
        # was skipped, since resource_skip_node still produces a real
        # AgentOutput to log.
        _log_agent_run(self.db, workflow_id, 1, AgentOutput(**req_output), input_summary={
            "appointment_request": ctx.get("appointment_request"),
            "location": ctx.get("location"),
            "appointment_type": ctx.get("appointment_type"),
        })
        _log_agent_run(self.db, workflow_id, 2, AgentOutput(**sch_output), input_summary={
            "requested_doctor": ctx.get("requested_doctor"),
            "doctor_availability": ctx.get("doctor_availability"),
            "existing_appointments_count": len(ctx.get("existing_appointments", [])),
            "flexibility_minutes": ctx.get("appointment_request", {}).get("flexibility_minutes"),
        })
        _log_agent_run(self.db, workflow_id, 3, AgentOutput(**que_output), input_summary={
            "queue_snapshot": ctx.get("queue_snapshot"),
        })
        _log_agent_run(self.db, workflow_id, 4, AgentOutput(**res_output), input_summary={
            "required_room_type": ctx.get("appointment_type", {}).get("required_room_type"),
            "rooms": ctx.get("rooms"),
            "resource_skipped": route_flags.get("resource_not_required", False),
        })
        _log_agent_run(self.db, workflow_id, 5, AgentOutput(**afu_output), input_summary={
            "confirmation_status": ctx.get("appointment_request", {}).get("confirmation_status"),
            "attendance_summary": ctx.get("attendance_summary"),
            "follow_up_summary": ctx.get("follow_up_summary"),
        })
        _log_agent_run(self.db, workflow_id, 6, AgentOutput(**decision_output), input_summary={
            "request_validation": req_output.get("classification"),
            "schedule": sch_output.get("classification"),
            "queue": que_output.get("classification"),
            "resource": res_output.get("classification"),
            "attendance_follow_up": afu_output.get("classification"),
        })

        wait_band = None
        que_recommendation = que_output.get("recommendation")
        if que_recommendation:
            wait_band = que_recommendation.replace(" minutes (estimate)", "")

        # executed_path: deterministic reconstruction from route_flags,
        # since the actual conditional edges already made this decision
        # inside the graph — this just reports it, matching what really
        # ran (verified structurally in workflow_graph.py's edges).
        executed_path = [
            "context_builder_node",
            "router_node",
            "appointment_request_node",
            "schedule_availability_node",
            "queue_load_node",
            "resource_skip_node" if route_flags.get("resource_not_required") else "resource_allocation_node",
            "attendance_follow_up_node",
            "appointment_operations_decision_node",
            "explanation_audit_node",
        ]
        skipped_agents = list(final_state.get("skipped_agents", []))

        response = {
            # --- Stage 3 fields (unchanged) ---
            "workflow_id": workflow_id,
            "graph_mode": "langgraph_stateless",
            "shared_state": ctx,
            "agent_trace": [
                {
                    "agent": o.get("agent_name"),
                    "classification": o.get("classification"),
                    "rules_triggered": o.get("rules_triggered"),
                }
                for o in (req_output, sch_output, que_output, res_output, afu_output, decision_output)
            ],
            "final_output": decision_output,
            "explanation": final_state.get("explanation", ""),
            "audit_reference": final_state.get("audit_reference"),
            "workflow_session_id": workflow_id,
            "appointment_request_id": appointment_request_id,
            "status": "completed",
            "request_validation": {"status": req_output.get("classification")},
            "schedule": {
                "category": sch_output.get("classification"),
                "doctor_code": ctx.get("requested_doctor", {}).get("doctor_code"),
                "date": ctx.get("appointment_request", {}).get("preferred_date"),
                "time": sch_output.get("recommendation")
                if sch_output.get("classification") == "Exact Slot Available"
                else ctx.get("appointment_request", {}).get("preferred_time"),
            },
            "queue": {
                "category": que_output.get("classification"),
                "projected_utilization_percent": que_output.get("evidence", {}).get(
                    "projected_utilization_percent"
                ),
                "estimated_wait_band_minutes": wait_band,
            },
            "resource": {"room_code": res_output.get("recommendation")},
            "attendance_follow_up": {
                "confirmation_action": afu_output.get("recommendation"),
                "follow_up_status": afu_output.get("evidence", {}).get("follow_up_status"),
            },
            "decision": {"category": decision_output.get("classification")},
            "reason_codes": final_state.get("final_recommendation", {}).get("reason_codes", []),
            # --- Stage 3.1: additive conditional-routing fields ---
            "conditional_routing": True,
            "selected_route": selected_route,
            "route_reason": route_reason,
            "route_flags": route_flags,
            "executed_path": executed_path,
            "skipped_agents": skipped_agents,
        }

        session_row.status = "completed"
        session_row.context_snapshot = ctx
        session_row.final_output_snapshot = response
        session_row.completed_at = datetime.now(timezone.utc)
        self.db.commit()

        return response
