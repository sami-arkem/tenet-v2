from __future__ import annotations

from pathlib import Path

from api.store import get_audit_detail
from core.audit_context_service import build_retrieval_grounded_context_pack
from core.context_execution_service import (
    build_execution_payload_from_context,
    ensure_context_pack_ready,
    execute_pack_via_context,
    execute_workflow_via_context,
)
from core.evidence_ingestion_service import ingest_evidence_file
from core.evidence_pack_service import create_evidence_pack
from core.evidence_processing_service import process_all_evidence_for_pack
from core.retrieval_service import build_pack_retrieval_index
from core.workflow_service import create_workflow


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


def seed_ready_pack(tmp_path: Path):
    pack = create_evidence_pack(
        name="Acme AML Pack",
        created_by="sami",
        manifest=make_manifest(),
        pack_root=tmp_path / "packs",
    )
    for filename, title, source_type, content in [
        ("policy.txt", "Monitoring Policy", "policy_document", b"AML transaction monitoring policy and escalation procedure."),
        ("screening.txt", "Screening Alerts", "screening_alert_log", b"Sanctions screening alert handling and OFAC escalation workflow."),
    ]:
        ingest_evidence_file(
            pack_id=pack["pack_id"],
            filename=filename,
            data=content,
            title=title,
            source_type=source_type,
            citation=f"{filename}#L1-L1",
            pack_root=tmp_path / "packs",
            evidence_root=tmp_path / "blobs",
        )
    process_all_evidence_for_pack(pack_id=pack["pack_id"], pack_root=tmp_path / "packs")
    build_pack_retrieval_index(pack_id=pack["pack_id"], pack_root=tmp_path / "packs")
    return pack


def test_ensure_context_pack_ready_and_payload(tmp_path: Path):
    pack = seed_ready_pack(tmp_path)
    ctx = build_retrieval_grounded_context_pack(
        pack_id=pack["pack_id"],
        pack_root=tmp_path / "packs",
    )
    checked = ensure_context_pack_ready(pack_id=pack["pack_id"], pack_root=tmp_path / "packs")
    assert checked["selected_chunk_count"] == ctx["selected_chunk_count"]

    payload = build_execution_payload_from_context(
        pack_id=pack["pack_id"],
        context_pack=checked,
        run_id="run_ctx_001",
        default_remediation_owner="compliance@acme.com",
        pack_root=tmp_path / "packs",
    )
    assert payload["run_id"] == "run_ctx_001"
    assert payload["audit_context_pack"]["deterministic_authoritative"] is True
    assert payload["metadata"]["context_gated_execution"] is True


def test_execute_pack_via_context_persists_context(tmp_path: Path):
    pack = seed_ready_pack(tmp_path)

    out = execute_pack_via_context(
        pack_id=pack["pack_id"],
        run_id="run_ctx_exec_001",
        default_remediation_owner="compliance@acme.com",
        pack_root=tmp_path / "packs",
    )
    assert out["run_id"] == "run_ctx_exec_001"
    assert out["context_pack"]["selected_chunk_count"] >= 1

    detail = get_audit_detail("run_ctx_exec_001")
    assert isinstance(detail["audit_context_pack"], dict)
    assert detail["audit_context_pack"]["deterministic_authoritative"] is True


def test_execute_workflow_via_context_updates_workflow(tmp_path: Path):
    pack = seed_ready_pack(tmp_path)
    workflow = create_workflow(
        pack_id=pack["pack_id"],
        created_by="sami",
        workflow_root=tmp_path / "workflows",
        pack_root=tmp_path / "packs",
    )

    out = execute_workflow_via_context(
        workflow_id=workflow["workflow_id"],
        run_id="run_ctx_workflow_001",
        default_remediation_owner="compliance@acme.com",
        workflow_root=tmp_path / "workflows",
        pack_root=tmp_path / "packs",
    )
    assert out["status"] == "AUDIT_EXECUTED"
    assert out["latest_context_pack"]["selected_chunk_count"] >= 1
    assert any(x["event_type"] == "context_gated_audit_executed" for x in out["timeline"])
