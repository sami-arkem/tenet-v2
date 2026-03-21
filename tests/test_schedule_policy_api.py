from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def _payload(latest_evidence_at: str) -> dict:
    return {
        "audit_type": "aml_readiness_review",
        "latest_evidence_at": latest_evidence_at,
        "regime_scope": ["AML"],
        "jurisdiction": "UK",
    }


def test_schedule_policy_api_flow():
    create_response = client.post(
        "/v1/schedule-policy",
        json={
            "tenant_id": "tenant_001",
            "created_by": "user_001",
            "name": "Quarterly AML Audit",
            "regime_scope": ["AML"],
            "jurisdiction": "UK",
            "frequency": "QUARTERLY",
            "next_run_date": "2026-03-25",
            "audit_payload": _payload("2026-03-15T00:00:00+00:00"),
            "notify_users": ["user_001"],
        },
    )
    assert create_response.status_code == 200
    schedule_id = create_response.json()["data"]["schedule_id"]

    list_response = client.get("/v1/schedule-policy")
    assert list_response.status_code == 200
    assert list_response.json()["data"]["count"] >= 1

    get_response = client.get(f"/v1/schedule-policy/{schedule_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["schedule_id"] == schedule_id

    eligibility_response = client.get(f"/v1/schedule-policy/{schedule_id}/eligibility")
    assert eligibility_response.status_code == 200
    assert eligibility_response.json()["data"]["eligible"] is False

    patch_response = client.patch(
        f"/v1/schedule-policy/{schedule_id}",
        json={
            "next_run_date": "2026-03-18",
            "audit_payload": _payload("2026-03-10T00:00:00+00:00"),
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["data"]["next_run_date"] == "2026-03-18"

    due_response = client.get("/v1/schedule-policy/planner/due?limit=10")
    assert due_response.status_code == 200
    due_data = due_response.json()["data"]
    assert due_data["eligible_count"] >= 1
    assert due_data["eligible_items"][0]["audit_run_request"]["trigger_type"] == "SCHEDULED_AUTO_RUN"

    reminders_response = client.get("/v1/schedule-policy/planner/reminders")
    assert reminders_response.status_code == 200

    mark_response = client.post(
        f"/v1/schedule-policy/{schedule_id}/mark-executed",
        json={
            "last_run_id": "TEN-20260318-aaaa1111",
            "executed_at": "2026-03-18T08:00:00+00:00",
        },
    )
    assert mark_response.status_code == 200
    assert mark_response.json()["data"]["last_run_id"] == "TEN-20260318-aaaa1111"

    delete_response = client.delete(f"/v1/schedule-policy/{schedule_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["deleted"] is True
