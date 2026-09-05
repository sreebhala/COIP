def test_context_build_success_for_confirmed_request(client, seed):
    response = client.post(
        "/api/v1/workflows/appointment-review/context",
        json={"appointment_request_id": "REQ-001"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["workflow_session"]["status"] in ("context_ready", "missing_configuration")
    assert body["workflow_session"]["appointment_request_id"]
    context = body["context"]
    assert context["clinic"]["clinic_code"] == "CLN-001"
    assert context["location"]["location_code"] == "LOC-001"
    assert context["requested_doctor"]["doctor_code"] == "DOC-001"
    assert context["doctor_availability"], "expected doctor availability to be loaded"
    assert "rooms" in context


def test_context_build_unknown_request_returns_404(client, seed):
    response = client.post(
        "/api/v1/workflows/appointment-review/context",
        json={"appointment_request_id": "REQ-999"},
    )
    assert response.status_code == 404


def test_emergency_flag_stops_workflow_safely(client, seed):
    # REQ-005 is seeded with emergency_flag_entered_by_staff = True
    response = client.post(
        "/api/v1/workflows/appointment-review/context",
        json={"appointment_request_id": "REQ-005"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "emergency_stop"
    assert "emergency" in body["message"].lower()


def test_context_is_retrievable_after_build(client, seed):
    build_response = client.post(
        "/api/v1/workflows/appointment-review/context",
        json={"appointment_request_id": "REQ-001"},
    )
    workflow_session_id = build_response.json()["workflow_session"]["workflow_session_id"]

    session_response = client.get(f"/api/v1/workflows/{workflow_session_id}")
    assert session_response.status_code == 200
    assert session_response.json()["workflow_session_id"] == workflow_session_id

    context_response = client.get(f"/api/v1/workflows/{workflow_session_id}/context")
    assert context_response.status_code == 200
    assert context_response.json()["clinic"]["clinic_code"] == "CLN-001"


def test_missing_queue_snapshot_is_flagged_not_fabricated(client, seed):
    # REQ-004 (14:00 slot) has no seeded QueueSnapshot row for that slot_time.
    response = client.post(
        "/api/v1/workflows/appointment-review/context",
        json={"appointment_request_id": "REQ-004"},
    )
    assert response.status_code == 200
    context = response.json()["context"]
    assert context["queue_snapshot"] == {}
    assert "no_queue_snapshot_for_requested_slot" in context["missing_data_flags"]
