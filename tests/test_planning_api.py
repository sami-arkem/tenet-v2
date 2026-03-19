from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def make_company_profile():
    return {
        "company_name": "Acme Fintech",
        "industry": "fintech",
        "primary_jurisdiction": "uk",
        "additional_jurisdictions": ["eu"],
        "products": ["payments"],
        "entities": ["Acme Fintech Ltd"],
    }


def make_scope():
    return {
        "audit_id": "audit_001",
        "audit_type": "aml_readiness_review",
        "framework_ids": ["UK_MLR", "EU_AMLD6"],
        "domain": "aml",
        "domains": ["aml"],
        "jurisdictions": ["uk", "eu"],
        "in_scope_entities": ["Acme Fintech Ltd"],
        "in_scope_products": ["payments"],
        "evaluation_date": "2026-03-18",
        "historical_context_is_non_authoritative": True,
        "deterministic_current_audit_truth_only": True,
    }


def make_manifest():
    return {
        "company_profile": make_company_profile(),
        "scope": make_scope(),
        "controls": [],
        "evidence_catalog": [
            {
                "evidence_id": "ev_001",
                "title": "Monitoring Policy",
                "source_type": "policy_document",
                "file_path": "evidence/policy.pdf",
                "citation": "policy.pdf#L1-L20",
            }
        ],
    }


def test_planning_scope_and_pack_flow():
    scope_response = client.post(
        "/v1/planning/scope",
        json={
            "company_profile": make_company_profile(),
            "scope": make_scope(),
        },
    )
    assert scope_response.status_code == 200
    scope_plan = scope_response.json()["data"]
    assert scope_plan["selected_control_count"] >= 1
    assert any(row["control_id"] == "AML.MONITORING.001" for row in scope_plan["selected_controls"])

    pack_response = client.post(
        "/v1/evidence-packs",
        json={
            "name": "Acme AML Pack",
            "created_by": "sami",
            "manifest": make_manifest(),
        },
    )
    assert pack_response.status_code == 200
    pack_id = pack_response.json()["data"]["pack_id"]

    plan_response = client.get(f"/v1/planning/evidence-packs/{pack_id}")
    assert plan_response.status_code == 200
    pack_plan = plan_response.json()["data"]
    assert pack_plan["pack_id"] == pack_id
    assert pack_plan["selected_control_count"] >= 1

    payload_response = client.get(f"/v1/planning/evidence-packs/{pack_id}/execution-payload")
    assert payload_response.status_code == 200
    payload = payload_response.json()["data"]["payload"]
    assert payload["metadata"]["planned_control_count"] >= 1
    assert len(payload["controls"]) >= 1


def test_planning_pack_not_found():
    response = client.get("/v1/planning/evidence-packs/does_not_exist")
    assert response.status_code == 404
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "HTTP_404"
