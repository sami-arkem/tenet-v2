from __future__ import annotations

from pathlib import Path

from core.evidence_ingestion_service import ingest_evidence_file
from core.evidence_pack_service import create_evidence_pack
from core.evidence_processing_service import process_all_evidence_for_pack
from core.workflow_service import (
    build_workflow_summary,
    create_workflow,
    execute_workflow_audit,
    list_workflows,
    refresh_workflow_readiness,
    refresh_workflow_remediation,
)


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


def test_workflow_end_to_end(tmp_path: Path):
    pack_root = tmp_path / "packs"

    created_pack = create_evidence_pack(
        name="Acme AML Pack",
        created_by="sami",
        manifest=make_manifest(),
        pack_root=pack_root,
    )

    ingest_evidence_file(
        pack_id=created_pack["pack_id"],
        filename="monitoring_policy.txt",
        data=b"Transaction monitoring policy for AML controls.\n",
        title="Monitoring Policy",
        source_type="policy_document",
        citation="monitoring_policy.txt#L1-L1",
        pack_root=pack_root,
        evidence_root=tmp_path / "blobs",
    )
    process_all_evidence_for_pack(
        pack_id=created_pack["pack_id"],
        pack_root=pack_root,
    )

    workflow = create_workflow(
        pack_id=created_pack["pack_id"],
        created_by="sami",
        workflow_root=tmp_path / "workflows",
        pack_root=pack_root,
    )
    workflow_id = workflow["workflow_id"]

    refreshed = refresh_workflow_readiness(
        workflow_id,
        workflow_root=tmp_path / "workflows",
        pack_root=pack_root,
    )
    assert refreshed["status"] == "READY_FOR_EXECUTION"

    executed = execute_workflow_audit(
        workflow_id=workflow_id,
        run_id="run_workflow_001",
        default_remediation_owner="compliance@acme.com",
        workflow_root=tmp_path / "workflows",
        pack_root=pack_root,
    )
    assert executed["status"] == "AUDIT_EXECUTED"

    rem = refresh_workflow_remediation(
        workflow_id,
        workflow_root=tmp_path / "workflows",
    )
    assert rem["latest_remediation_summary"]["item_count"] >= 0

    summary = build_workflow_summary(workflow_id, workflow_root=tmp_path / "workflows")
    assert summary["workflow_id"] == workflow_id
    assert len(summary["timeline"]) >= 4

    rows = list_workflows(workflow_root=tmp_path / "workflows")
    assert len(rows) == 1
