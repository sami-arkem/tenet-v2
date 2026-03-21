from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def make_manifest():
    return {
        "company_profile": {
            "company_name": "Acme Fintech",
            "industry": "fintech",
            "primary_jurisdiction": "uk",
            "additional_jurisdictions": ["eu"],
            "products": ["payments"],
            "entities": ["Acme Fintech Ltd"],
        },
        "scope": {
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
        },
        "controls": [],
        "evidence_catalog": [],
    }


def test_audit_context_api_flow():
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

    for filename, title, source_type, content in [
        ("policy.txt", "Monitoring Policy", "policy_document", b"AML transaction monitoring policy and escalation procedure."),
        ("screening.txt", "Screening Alerts", "screening_alert_log", b"Sanctions screening alert handling and OFAC escalation workflow."),
    ]:
        upload_response = client.post(
            f"/v1/evidence-packs/{pack_id}/evidence/upload",
            json={
                "filename": filename,
                "title": title,
                "source_type": source_type,
                "citation": f"{filename}#L1-L1",
                "content_base64": base64.b64encode(content).decode("ascii"),
            },
        )
        assert upload_response.status_code == 200

    process_response = client.post(f"/v1/evidence-packs/{pack_id}/processing/run")
    assert process_response.status_code == 200

    build_retrieval = client.post(
        f"/v1/retrieval/evidence-packs/{pack_id}/build",
        json={"chunk_token_target": 40, "chunk_overlap": 10},
    )
    assert build_retrieval.status_code == 200

    questions_response = client.get(f"/v1/audit-context/evidence-packs/{pack_id}/questions")
    assert questions_response.status_code == 200
    assert len(questions_response.json()["data"]["questions"]) >= 1

    build_context = client.post(
        f"/v1/audit-context/evidence-packs/{pack_id}/build",
        json={"top_k_per_question": 3, "ensure_retrieval_index": True},
    )
    assert build_context.status_code == 200
    data = build_context.json()["data"]
    assert data["deterministic_authoritative"] is True
    assert data["selected_chunk_count"] >= 1
    assert data["question_count"] >= 1

    get_context = client.get(f"/v1/audit-context/evidence-packs/{pack_id}")
    assert get_context.status_code == 200
    assert get_context.json()["data"]["pack_id"] == pack_id
