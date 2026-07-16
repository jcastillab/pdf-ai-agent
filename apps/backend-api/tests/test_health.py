from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_operational_endpoints_and_request_id() -> None:
    client = TestClient(app)
    request_id = "test-correlation-id"
    ready = client.get("/api/v1/ready", headers={"X-Request-ID": request_id})
    version = client.get("/api/v1/version")

    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}
    assert ready.headers["X-Request-ID"] == request_id
    assert version.json() == {"version": "0.1.0"}
