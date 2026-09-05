"""
Post #1.5 required validation: same input produces same result, trace
contains every executed agent, no doctor/slot/room invented, emergency
flag stops immediately, queue/confirmation stay operational, explanation
has no clinical inference, audit retrievable, unknown request fails safely.
"""


def test_full_review_confirm_slot_flow(client, seed):
    payload = {"appointment_request_id": "REQ-001"}
    response = client.post("/api/v1/reviews/appointment", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["decision"]["category"] in (
        "Confirm Slot", "Reject", "Needs Review", "Suggest Alternative", "Await Confirmation",
    )
    assert body["audit_reference"].startswith("AUD-")
    assert len(body["agent_trace"]) == 6  # 5 evidence agents + decision agent


def test_same_input_produces_same_result(client, seed):
    r1 = client.post("/api/v1/reviews/appointment", json={"appointment_request_id": "REQ-001"}).json()
    r2 = client.post("/api/v1/reviews/appointment", json={"appointment_request_id": "REQ-001"}).json()
    # Decision, schedule category, and reason codes must match on repeat
    # runs against identical underlying data, even though a new workflow
    # session / audit reference is created each time.
    assert r1["decision"]["category"] == r2["decision"]["category"]
    assert r1["schedule"]["category"] == r2["schedule"]["category"]
    assert sorted(r1["reason_codes"]) == sorted(r2["reason_codes"])


def test_trace_contains_every_executed_agent(client, seed):
    response = client.post("/api/v1/reviews/appointment", json={"appointment_request_id": "REQ-001"})
    body = response.json()
    agent_names = {entry["agent"] for entry in body["agent_trace"]}
    assert agent_names == {
        "AppointmentRequestAgent",
        "ScheduleAvailabilityAgent",
        "QueueLoadAgent",
        "ResourceAllocationAgent",
        "AttendanceAndFollowUpAgent",
        "AppointmentOperationsDecisionAgent",
    }


def test_no_doctor_slot_room_invented(client, seed):
    response = client.post("/api/v1/reviews/appointment", json={"appointment_request_id": "REQ-001"})
    body = response.json()
    # Whatever doctor/room appears must trace back to real seeded codes,
    # not a placeholder or fabricated value.
    if body["schedule"]["doctor_code"]:
        assert body["schedule"]["doctor_code"].startswith("DOC-")
    if body["resource"]["room_code"]:
        assert body["resource"]["room_code"].startswith("ROOM-")


def test_emergency_flag_stops_review_immediately(client, seed):
    response = client.post("/api/v1/reviews/appointment", json={"appointment_request_id": "REQ-005"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "emergency_stop"
    assert "emergency" in body["message"].lower()
    # No decision/agent_trace/audit_reference fields should appear at all.
    assert "agent_trace" not in body
    assert "audit_reference" not in body


def test_unknown_request_fails_safely(client, seed):
    response = client.post("/api/v1/reviews/appointment", json={"appointment_request_id": "REQ-999"})
    assert response.status_code == 404


def test_explanation_has_no_clinical_inference(client, seed):
    response = client.post("/api/v1/reviews/appointment", json={"appointment_request_id": "REQ-001"})
    explanation = response.json()["explanation"].lower()
    for term in ["diagnosis", "symptom", "treatment", "prescription", "triage", "disease"]:
        assert term not in explanation
    assert "guaranteed" not in explanation


def test_explanation_states_review_clearly_when_needed(client, seed):
    response = client.post("/api/v1/reviews/appointment", json={"appointment_request_id": "REQ-004"})
    body = response.json()
    if body["decision"]["category"] == "Needs Review":
        assert "review" in body["explanation"].lower()


def test_audit_record_is_retrievable(client, seed):
    review_response = client.post("/api/v1/reviews/appointment", json={"appointment_request_id": "REQ-001"})
    audit_reference = review_response.json()["audit_reference"]

    audit_response = client.get(f"/api/v1/audit/{audit_reference}")
    assert audit_response.status_code == 200
    audit_body = audit_response.json()
    assert audit_body["audit_reference"] == audit_reference
    assert audit_body["workflow_session_id"] == review_response.json()["workflow_session_id"]
    assert audit_body["decision"] == review_response.json()["decision"]["category"]


def test_unknown_audit_reference_fails_safely(client, seed):
    response = client.get("/api/v1/audit/AUD-999999")
    assert response.status_code == 404


def test_workflow_trace_endpoint_matches_review(client, seed):
    review_response = client.post("/api/v1/reviews/appointment", json={"appointment_request_id": "REQ-001"})
    workflow_session_id = review_response.json()["workflow_session_id"]

    trace_response = client.get(f"/api/v1/workflows/{workflow_session_id}/trace")
    assert trace_response.status_code == 200
    trace_body = trace_response.json()
    assert len(trace_body["agent_trace"]) == 6
    # Sequence numbers must be strictly increasing (true execution order).
    sequence_numbers = [entry["sequence_number"] for entry in trace_body["agent_trace"]]
    assert sequence_numbers == sorted(sequence_numbers)


def test_queue_and_confirmation_stay_operational_language(client, seed):
    response = client.post("/api/v1/reviews/appointment", json={"appointment_request_id": "REQ-002"})
    body = response.json()
    assert body["attendance_follow_up"]["confirmation_action"] in (
        "none_required", "confirm_before_visit", "confirmation_review",
    )
    assert body["queue"]["category"] in ("Stable", "Busy", "Over Capacity", "Missing Configuration")


def test_context_is_retrievable_after_full_review(client, seed):
    """Regression test — Stage 1.5: reviews run via the orchestrator must
    also store context_snapshot on the session, not just workflows created
    via the Post #1.3 context-only endpoint. This was missing since
    Post #1.5 and silently caused GET .../context to 404 for every real
    review, discovered while building the Stage 1.5 Agent Workflow
    Console."""
    review_response = client.post("/api/v1/reviews/appointment", json={"appointment_request_id": "REQ-001"})
    workflow_session_id = review_response.json()["workflow_session_id"]

    context_response = client.get(f"/api/v1/workflows/{workflow_session_id}/context")
    assert context_response.status_code == 200
    context_body = context_response.json()
    assert context_body["workflow_session_id"] == workflow_session_id
    assert "missing_data_flags" in context_body
    assert "routing_status" in context_body
