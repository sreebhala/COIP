def test_unknown_appointment_request_returns_404(client):
    response = client.get("/api/v1/appointment-requests/UNKNOWN")
    assert response.status_code == 404
