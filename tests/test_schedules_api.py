from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_schedules_api_flow():
    create_response = client.post(
        "/v1/schedules",
        json={
            "tenant_id": "tenant_001",
            "name": "Weekly AML Audit",
            "frequency": "WEEKLY",
            "starts_at": "2026-03-18T06:00:00+00:00",
            "timezone": "Europe/London",
            "audit_payload": {"audit_type": "aml_readiness_review"},
            "weekdays": ["WE"],
        },
    )
    assert create_response.status_code == 200
    schedule_id = create_response.json()["data"]["schedule_id"]

    list_response = client.get("/v1/schedules")
    assert list_response.status_code == 200
    assert list_response.json()["data"]["count"] >= 1

    get_response = client.get(f"/v1/schedules/{schedule_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["schedule_id"] == schedule_id

    patch_response = client.patch(
        f"/v1/schedules/{schedule_id}",
        json={"status": "PAUSED"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["data"]["status"] == "PAUSED"

    delete_response = client.delete(f"/v1/schedules/{schedule_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["deleted"] is True
