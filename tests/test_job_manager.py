from __future__ import annotations

import time
from pathlib import Path

from core.evidence_ingestion_service import ingest_evidence_file
from core.evidence_pack_service import create_evidence_pack
from core.job_manager import get_job, submit_job
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


def wait_for_job(job_id: str, job_root: Path, timeout: float = 5.0):
    started = time.time()
    while time.time() - started < timeout:
        row = get_job(job_id, job_root=job_root)
        if row["status"] in {"SUCCEEDED", "FAILED"}:
            return row
        time.sleep(0.05)
    raise AssertionError(f"job did not finish in time: {job_id}")


def test_process_evidence_pack_job(tmp_path: Path, monkeypatch):
    from core import evidence_ingestion_service, evidence_pack_service, evidence_processing_service, job_manager

    monkeypatch.setattr(evidence_pack_service, "DEFAULT_PACK_ROOT", tmp_path / "packs")
    monkeypatch.setattr(evidence_ingestion_service, "DEFAULT_PACK_ROOT", tmp_path / "packs")
    monkeypatch.setattr(evidence_ingestion_service, "DEFAULT_EVIDENCE_ROOT", tmp_path / "blobs")
    monkeypatch.setattr(evidence_processing_service, "DEFAULT_PACK_ROOT", tmp_path / "packs")
    monkeypatch.setattr(job_manager, "DEFAULT_JOB_ROOT", tmp_path / "jobs")

    pack = create_evidence_pack(
        name="Acme AML Pack",
        created_by="sami",
        manifest=make_manifest(),
        pack_root=tmp_path / "packs",
    )

    ingest_evidence_file(
        pack_id=pack["pack_id"],
        filename="monitoring_policy.txt",
        data=b"Transaction monitoring policy for AML controls.\n",
        title="Monitoring Policy",
        source_type="policy_document",
        citation="monitoring_policy.txt#L1-L1",
        pack_root=tmp_path / "packs",
        evidence_root=tmp_path / "blobs",
    )

    job = submit_job(
        job_type="process_evidence_pack",
        payload={"pack_id": pack["pack_id"]},
        job_root=tmp_path / "jobs",
    )
    finished = wait_for_job(job["job_id"], job_root=tmp_path / "jobs")
    assert finished["status"] == "SUCCEEDED"
    assert finished["result"]["readiness"]["corpus_ready"] is True


def test_run_workflow_audit_job(tmp_path: Path, monkeypatch):
    from core import evidence_ingestion_service, evidence_pack_service, evidence_processing_service, workflow_service, job_manager

    monkeypatch.setattr(evidence_pack_service, "DEFAULT_PACK_ROOT", tmp_path / "packs")
    monkeypatch.setattr(evidence_ingestion_service, "DEFAULT_PACK_ROOT", tmp_path / "packs")
    monkeypatch.setattr(evidence_ingestion_service, "DEFAULT_EVIDENCE_ROOT", tmp_path / "blobs")
    monkeypatch.setattr(evidence_processing_service, "DEFAULT_PACK_ROOT", tmp_path / "packs")
    monkeypatch.setattr(workflow_service, "DEFAULT_WORKFLOW_ROOT", tmp_path / "workflows")
    monkeypatch.setattr(workflow_service, "DEFAULT_PACK_ROOT", tmp_path / "packs")
    monkeypatch.setattr(job_manager, "DEFAULT_JOB_ROOT", tmp_path / "jobs")

    pack = create_evidence_pack(
        name="Acme AML Pack",
        created_by="sami",
        manifest=make_manifest(),
        pack_root=tmp_path / "packs",
    )
    ingest_evidence_file(
        pack_id=pack["pack_id"],
        filename="monitoring_policy.txt",
        data=b"Transaction monitoring policy for AML controls.\n",
        title="Monitoring Policy",
        source_type="policy_document",
        citation="monitoring_policy.txt#L1-L1",
        pack_root=tmp_path / "packs",
        evidence_root=tmp_path / "blobs",
    )
    evidence_processing_service.process_all_evidence_for_pack(pack_id=pack["pack_id"], pack_root=tmp_path / "packs")

    workflow = create_workflow(
        pack_id=pack["pack_id"],
        created_by="sami",
        workflow_root=tmp_path / "workflows",
        pack_root=tmp_path / "packs",
    )

    job = submit_job(
        job_type="run_workflow_audit",
        payload={
            "workflow_id": workflow["workflow_id"],
            "run_id": "run_job_workflow_001",
            "default_remediation_owner": "compliance@acme.com",
        },
        job_root=tmp_path / "jobs",
    )
    finished = wait_for_job(job["job_id"], job_root=tmp_path / "jobs", timeout=10.0)
    assert finished["status"] == "SUCCEEDED"
    assert finished["result"]["latest_execution"]["run_id"] == "run_job_workflow_001"
