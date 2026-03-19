from fastapi.testclient import TestClient

from apps.api.main import create_app


def test_health_and_ready_are_public() -> None:
    client = TestClient(create_app())

    health = client.get("/health")
    ready = client.get("/ready")

    assert health.status_code == 200
    assert ready.status_code == 200
    assert health.json()["status"] == "ok"
    assert ready.json()["status"] == "ready"
