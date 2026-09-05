"""
Conditional LangGraph Routing Tests — Stage 3.1.

Covers the 4 grounded routes identified in the Post 5 discovery comment.
REQ-001..REQ-005 come from the existing Stage 1 seed data. REQ-006 and
REQ-007 are new seed additions (see seed.py) that exercise two real,
already-implemented code paths — missing_configuration and
resource-not-required — that no existing seeded request happened to
trigger. They are not new business logic, just new fixtures for
already-real conditions.
"""


def test_standard_route(client, seed):
    """REQ-001: complete case, no exception trigger — full agent sequence,
    nothing skipped."""
    response = client.post("/api/v1/graph/reviews/appointment", json={"appointment_request_id": "REQ-001"})
    body = response.json()

    assert response.status_code == 200
    assert body["selected_route"] == "standard"
    assert body["route_flags"]["has_missing_data"] is False
    assert body["route_flags"]["requires_human_review"] is False
    assert body["route_flags"]["resource_not_required"] is False
    assert body["skipped_agents"] == []
    assert "resource_allocation_node" in body["executed_path"]
    assert "resource_skip_node" not in body["executed_path"]
    assert len(body["agent_trace"]) == 6
    assert body["audit_reference"] is not None


def test_emergency_human_review_route(client, seed):
    """REQ-005: emergency flag — all 6 agents skipped, routed directly to
    human review. No audit record, matching the deterministic endpoint's
    emergency-stop behavior exactly (Stage 3 behavior, unchanged here)."""
    response = client.post("/api/v1/graph/reviews/appointment", json={"appointment_request_id": "REQ-005"})
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "emergency_stop"
    assert body["selected_route"] == "emergency_human_review"
    assert body["route_flags"]["requires_human_review"] is True
    assert len(body["skipped_agents"]) == 6
    assert body["executed_path"] == ["context_builder_node", "explanation_audit_node"]
    assert "audit_reference" not in body


def test_missing_configuration_route(client, seed):
    """REQ-006: requested doctor (DOC-003) has zero seeded availability
    rows, so ContextBuilder sets routing_status="missing_configuration".
    Option A (from the Post 5 discovery comment): all 6 agents still run
    — nothing is skipped — so the graph's output stays comparable in
    shape to what the legacy endpoint would produce for the same input.
    Only the route label/reason differ."""
    response = client.post("/api/v1/graph/reviews/appointment", json={"appointment_request_id": "REQ-006"})
    body = response.json()

    assert response.status_code == 200
    assert body["selected_route"] == "missing_configuration_review"
    assert body["route_flags"]["has_missing_data"] is True
    assert body["skipped_agents"] == []
    assert len(body["agent_trace"]) == 6


def test_resource_not_required_route(client, seed):
    """REQ-007: appointment type APT-TELE has no required_room_type, so
    ResourceAllocationAgent's output ("Not Required") is known in advance
    and the node is skipped in favor of resource_skip_node."""
    response = client.post("/api/v1/graph/reviews/appointment", json={"appointment_request_id": "REQ-007"})
    body = response.json()

    assert response.status_code == 200
    assert body["selected_route"] == "resource_not_required"
    assert body["route_flags"]["resource_not_required"] is True
    assert len(body["skipped_agents"]) == 1
    assert body["skipped_agents"][0]["agent"] == "ResourceAllocationAgent"
    assert "resource_skip_node" in body["executed_path"]
    assert "resource_allocation_node" not in body["executed_path"]
    assert body["resource"]["room_code"] is None

    resource_trace_entry = next(a for a in body["agent_trace"] if a["agent"] == "ResourceAllocationAgent")
    assert resource_trace_entry["classification"] == "Not Required"
    assert "COIP-RES-003" in resource_trace_entry["rules_triggered"]


def test_resource_skip_matches_legacy_endpoint_output(client, seed):
    """The one route that actually skips an agent must still produce a
    final decision identical to the legacy endpoint's for the same input
    — proving the skip is safe, not just fast."""
    old = client.post("/api/v1/reviews/appointment", json={"appointment_request_id": "REQ-007"}).json()
    new = client.post("/api/v1/graph/reviews/appointment", json={"appointment_request_id": "REQ-007"}).json()

    assert old["decision"]["category"] == new["decision"]["category"]
    assert old["resource"]["room_code"] == new["resource"]["room_code"]
    assert sorted(old["reason_codes"]) == sorted(new["reason_codes"])


def test_route_decision_is_recorded_in_audit(client, seed):
    """Route decision must be retrievable from the audit trail, not just
    the response body — per the 'Record route decision in audit if audit
    exists' backend expectation."""
    response = client.post("/api/v1/graph/reviews/appointment", json={"appointment_request_id": "REQ-007"})
    audit_reference = response.json()["audit_reference"]

    audit_response = client.get(f"/api/v1/audit/{audit_reference}")
    assert audit_response.status_code == 200

    evidence = audit_response.json()["evidence"]
    assert "routing" in evidence
    assert evidence["routing"]["selected_route"] == "resource_not_required"


def test_stage3_graph_endpoint_shape_still_present(client, seed):
    """Stage 3.1 fields are additive — every Stage 3 field must still be
    present and unchanged in shape, so this endpoint still satisfies the
    Stage 3 old-vs-graph comparison tests."""
    response = client.post("/api/v1/graph/reviews/appointment", json={"appointment_request_id": "REQ-001"})
    body = response.json()

    for key in (
        "workflow_id", "graph_mode", "shared_state", "agent_trace",
        "final_output", "explanation", "audit_reference",
    ):
        assert key in body
    assert body["graph_mode"] == "langgraph_stateless"
