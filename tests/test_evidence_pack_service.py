from __future__ import annotations

from core.evidence_ingestion_service import ingest_evidence_file
from core.evidence_pack_service import (
    create_evidence_pack,
    execute_evidence_pack,
    get_evidence_pack,
    list_evidence_packs,
)
from core.evidence_processing_service import process_all_evidence_for_pack


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
        "prior_historical_context": {"prior_findings": 2},
        "metadata": {"source": "unit_test"},
    }


def test_create_get_list_and_execute(tmp_path):
    created = create_evidence_pack(
        name="Acme AML Pack",
        created_by="sami",
        manifest=make_manifest(),
        pack_root=tmp_path,
    )
    assert created["status"] == "READY"
    pack_id = created["pack_id"]

    loaded = get_evidence_pack(pack_id, pack_root=tmp_path)
    assert loaded["detail"]["pack_id"] == pack_id
    assert loaded["manifest"]["scope"]["audit_type"] == "aml_readiness_review"

    listed = list_evidence_packs(pack_root=tmp_path)
    assert len(listed) == 1
    assert listed[0]["pack_id"] == pack_id

    ingest_evidence_file(
        pack_id=pack_id,
        filename="monitoring_policy.txt",
        data=b"Transaction monitoring policy for AML controls.\n",
        title="Monitoring Policy",
        source_type="policy_document",
        citation="monitoring_policy.txt#L1-L1",
        pack_root=tmp_path,
        evidence_root=tmp_path / "blobs",
    )
    process_all_evidence_for_pack(
        pack_id=pack_id,
        pack_root=tmp_path,
    )

    executed = execute_evidence_pack(
        pack_id=pack_id,
        run_id="run_aml_001",
        default_remediation_owner="compliance@acme.com",
        metadata={"executed_from": "test"},
        pack_root=tmp_path,
    )
    assert executed["pack_id"] == pack_id
    assert executed["execution"]["run_id"] == "run_aml_001"
    assert executed["execution"]["topline"]["deployment_decision"] == "CONDITIONALLY_APPROVED"

    loaded_after = get_evidence_pack(pack_id, pack_root=tmp_path)
    assert loaded_after["detail"]["latest_execution"]["run_id"] == "run_aml_001"
