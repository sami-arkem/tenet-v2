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
            "framework_ids": ["UK_MLR"],
            "domain": "aml",
            "domains": ["aml"],
            "jurisdictions": ["uk"],
            "in_scope_entities": ["Acme Fintech Ltd"],
            "in_scope_products": ["payments"],
            "evaluation_date": "2026-03-18",
            "historical_context_is_non_authoritative": True,
            "deterministic_current_audit_truth_only": True,
        },
        "controls": [],
        "evidence_catalog": [],
    }


def test_retrieval_api_flow():
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

    build_response = client.post(
        f"/v1/retrieval/evidence-packs/{pack_id}/build",
        json={"chunk_token_target": 40, "chunk_overlap": 10},
    )
    assert build_response.status_code == 200
    assert build_response.json()["data"]["document_count"] == 2

    search_response = client.post(
        f"/v1/retrieval/evidence-packs/{pack_id}/search",
        json={"query": "transaction monitoring escalation", "top_k": 5},
    )
    assert search_response.status_code == 200
    assert search_response.json()["data"]["result_count"] >= 1

    context_response = client.post(
        f"/v1/retrieval/evidence-packs/{pack_id}/audit-context",
        json={
            "audit_questions": [
                "What evidence supports transaction monitoring?",
                "What evidence supports sanctions screening?",
            ],
            "top_k_per_question": 3,
        },
    )
    assert context_response.status_code == 200
    data = context_response.json()["data"]
    assert data["question_count"] == 2
    assert data["selected_chunk_count"] >= 1
