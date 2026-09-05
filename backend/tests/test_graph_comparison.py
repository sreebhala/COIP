"""
Old vs Graph Comparison Tests — Stage 3 (LangGraph Stateless).

Runs the same appointment_request_id through both the existing
deterministic endpoint and the new graph endpoint and asserts the
operationally meaningful fields match. workflow_session_id and
audit_reference are expected to differ between the two calls (each call
creates a new WorkflowSession, exactly like calling the deterministic
endpoint twice already does in test_same_input_produces_same_result) —
that is documented as the one intentional difference, not a bug.
"""


def test_graph_matches_deterministic_confirm_slot_flow(client, seed):
    old = client.post("/api/v1/reviews/appointment", json={"appointment_request_id": "REQ-001"}).json()
    new = client.post("/api/v1/graph/reviews/appointment", json={"appointment_request_id": "REQ-001"}).json()

    assert new["graph_mode"] == "langgraph_stateless"
    assert old["decision"]["category"] == new["decision"]["category"]
    assert old["schedule"]["category"] == new["schedule"]["category"]
    assert old["resource"]["room_code"] == new["resource"]["room_code"]
    assert sorted(old["reason_codes"]) == sorted(new["reason_codes"])

    old_agents = [a["agent"] for a in old["agent_trace"]]
    new_agents = [a["agent"] for a in new["agent_trace"]]
    assert old_agents == new_agents == [
        "AppointmentRequestAgent",
        "ScheduleAvailabilityAgent",
        "QueueLoadAgent",
        "ResourceAllocationAgent",
        "AttendanceAndFollowUpAgent",
        "AppointmentOperationsDecisionAgent",
    ]


def test_graph_matches_deterministic_emergency_stop(client, seed):
    old = client.post("/api/v1/reviews/appointment", json={"appointment_request_id": "REQ-005"}).json()
    new = client.post("/api/v1/graph/reviews/appointment", json={"appointment_request_id": "REQ-005"}).json()

    assert old["status"] == "emergency_stop"
    assert new["status"] == "emergency_stop"
    assert "agent_trace" not in new
    assert "audit_reference" not in new

    # Field-level parity, not just status: every key the deterministic
    # endpoint returns for emergency-stop must also be present in the graph
    # endpoint's response. workflow_session_id legitimately differs (each
    # call creates a new session, same as calling the old endpoint twice);
    # appointment_request_id/status/message must match exactly.
    assert "workflow_session_id" in new, "graph emergency-stop response is missing 'workflow_session_id'"
    for key in ("appointment_request_id", "status", "message"):
        assert key in new, f"graph emergency-stop response is missing '{key}'"
        assert old[key] == new[key], f"'{key}' differs: old={old[key]!r} new={new[key]!r}"


def test_graph_unknown_request_fails_safely(client, seed):
    response = client.post("/api/v1/graph/reviews/appointment", json={"appointment_request_id": "REQ-999"})
    assert response.status_code == 404


def test_graph_explanation_has_no_clinical_inference(client, seed):
    response = client.post("/api/v1/graph/reviews/appointment", json={"appointment_request_id": "REQ-001"})
    explanation = response.json()["explanation"].lower()
    for term in ["diagnosis", "symptom", "treatment", "prescription", "triage", "disease"]:
        assert term not in explanation


def test_graph_session_trace_is_persisted_and_retrievable(client, seed):
    """
    Confirms graph-run agent executions are written to AgentExecutionLog,
    not just returned in the graph response body — so
    GET /api/v1/workflows/{id}/trace works identically for graph sessions
    as it does for deterministic-run sessions.
    """
    graph_response = client.post(
        "/api/v1/graph/reviews/appointment", json={"appointment_request_id": "REQ-001"}
    ).json()
    workflow_id = graph_response["workflow_id"]

    trace_response = client.get(f"/api/v1/workflows/{workflow_id}/trace")
    assert trace_response.status_code == 200

    persisted_trace = trace_response.json()["agent_trace"]
    persisted_agents = [entry["agent_name"] for entry in persisted_trace]
    assert persisted_agents == [
        "AppointmentRequestAgent",
        "ScheduleAvailabilityAgent",
        "QueueLoadAgent",
        "ResourceAllocationAgent",
        "AttendanceAndFollowUpAgent",
        "AppointmentOperationsDecisionAgent",
    ]
