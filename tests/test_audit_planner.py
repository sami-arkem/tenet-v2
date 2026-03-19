from __future__ import annotations

from core.audit_planner import (
    build_audit_plan_from_scope,
    build_execution_payload_from_pack,
    control_applies,
)
from core.control_library import build_default_control_library
from core.evidence_pack_service import create_evidence_pack


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
            },
            {
                "evidence_id": "ev_002",
                "title": "CDD Policy",
                "source_type": "cdd_policy",
                "file_path": "evidence/cdd.pdf",
                "citation": "cdd.pdf#L1-L15",
            },
        ],
        "prior_historical_context": {"prior_findings": 2},
        "metadata": {"source": "unit_test"},
    }


def test_control_applies():
    control = build_default_control_library()[0]
    applies, reasons = control_applies(
        control=control,
        domains=["aml"],
        jurisdictions=["uk"],
        framework_ids=["UK_MLR"],
        entity_types=["regulated_entity", "fintech"],
        product_tags=["payments"],
    )
    assert applies is True
    assert "domain_match" in reasons
    assert "framework_match" in reasons


def test_build_audit_plan_from_scope():
    plan = build_audit_plan_from_scope(
        company_profile=make_company_profile(),
        scope=make_scope(),
    )
    assert plan["selected_control_count"] >= 2
    assert any(row["control_id"] == "AML.MONITORING.001" for row in plan["selected_controls"])


def test_build_execution_payload_from_pack(tmp_path):
    created = create_evidence_pack(
        name="Acme AML Pack",
        created_by="sami",
        manifest=make_manifest(),
        pack_root=tmp_path,
    )
    payload = build_execution_payload_from_pack(created["pack_id"], pack_root=tmp_path)
    assert payload["company_profile"]["company_name"] == "Acme Fintech"
    assert payload["metadata"]["planned_control_count"] >= 1
    assert len(payload["controls"]) >= 1
    assert payload["controls"][0]["control"]["control_id"]
