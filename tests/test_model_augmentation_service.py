from __future__ import annotations

from pathlib import Path

from api.store import execute_and_store_audit
from core.evidence_ingestion_service import ingest_evidence_file
from core.evidence_pack_service import create_evidence_pack
from core.evidence_processing_service import process_all_evidence_for_pack
from core.model_augmentation_service import (
    augment_audit_report_with_models,
    augment_evidence_item_with_models,
    augment_pack_evidence_with_models,
    get_audit_report_augmentation,
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
        "controls": [
            {
                "control": {
                    "control_id": "AML.MONITORING.001",
                    "regime_id": "UK_MLR.001",
                    "title": "Transaction monitoring policy",
                    "description": "A documented transaction monitoring control must exist.",
                    "test_procedure": "Check for policy and monitoring evidence.",
                    "required_evidence_types": ["policy_document", "monitoring_report"],
                    "severity_if_missing": "HIGH",
                },
                "provided_evidence": [
                    {
                        "evidence_id": "ev_001",
                        "title": "Monitoring Policy",
                        "source_type": "policy_document",
                        "file_path": "evidence/policy.pdf",
                        "citation": "policy.pdf#L1-L20",
                    }
                ],
                "declared_control_present": True,
                "declared_operating_effective": True,
            }
        ],
        "evidence_catalog": [],
    }


def make_audit_payload():
    return {
        "run_id": "run_model_aug_001",
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
        "controls": [
            {
                "control": {
                    "control_id": "AML.MONITORING.001",
                    "regime_id": "UK_MLR.001",
                    "title": "Transaction monitoring policy",
                    "description": "A documented transaction monitoring control must exist.",
                    "test_procedure": "Check for policy and monitoring evidence.",
                    "required_evidence_types": ["policy_document", "monitoring_report"],
                    "severity_if_missing": "HIGH",
                },
                "provided_evidence": [
                    {
                        "evidence_id": "ev_001",
                        "title": "Monitoring Policy",
                        "source_type": "policy_document",
                        "file_path": "evidence/policy.pdf",
                        "citation": "policy.pdf#L1-L20",
                    }
                ],
                "declared_control_present": True,
                "declared_operating_effective": True,
                "notes": "Policy exists but monitoring evidence is incomplete.",
            }
        ],
        "default_remediation_owner": "compliance@acme.com",
    }


def test_augment_evidence_and_pack(tmp_path: Path, monkeypatch):
    from core import evidence_ingestion_service, evidence_pack_service, evidence_processing_service, model_augmentation_service

    monkeypatch.setattr(evidence_pack_service, "DEFAULT_PACK_ROOT", tmp_path / "packs")
    monkeypatch.setattr(evidence_ingestion_service, "DEFAULT_PACK_ROOT", tmp_path / "packs")
    monkeypatch.setattr(evidence_ingestion_service, "DEFAULT_EVIDENCE_ROOT", tmp_path / "blobs")
    monkeypatch.setattr(evidence_processing_service, "DEFAULT_PACK_ROOT", tmp_path / "packs")
    monkeypatch.setattr(model_augmentation_service, "DEFAULT_PACK_ROOT", tmp_path / "packs")

    pack = create_evidence_pack(
        name="Acme AML Pack",
        created_by="sami",
        manifest=make_manifest(),
        pack_root=tmp_path / "packs",
    )
    item = ingest_evidence_file(
        pack_id=pack["pack_id"],
        filename="policy.txt",
        data=b"AML policy and procedure for transaction monitoring.",
        title="Monitoring Policy",
        source_type="policy_document",
        citation="policy.txt#L1-L1",
        pack_root=tmp_path / "packs",
        evidence_root=tmp_path / "blobs",
    )
    process_all_evidence_for_pack(pack_id=pack["pack_id"], pack_root=tmp_path / "packs")

    out = augment_evidence_item_with_models(
        pack_id=pack["pack_id"],
        evidence_id=item["evidence_id"],
        pack_root=tmp_path / "packs",
    )
    assert out["non_authoritative"] is True
    assert out["classification"]["label"]

    bulk = augment_pack_evidence_with_models(
        pack_id=pack["pack_id"],
        pack_root=tmp_path / "packs",
    )
    assert bulk["augmented_count"] == 1
    assert bulk["failure_count"] == 0


def test_augment_audit_report(tmp_path: Path, monkeypatch):
    from core import model_augmentation_service

    monkeypatch.setattr(model_augmentation_service, "DEFAULT_AUDIT_ROOT", tmp_path / "runs")

    execute_and_store_audit(
        payload=make_audit_payload(),
        store_root=tmp_path / "runs",
    )

    out = augment_audit_report_with_models(
        run_id="run_model_aug_001",
        audit_root=tmp_path / "runs",
    )
    assert out["non_authoritative"] is True
    assert "executive_narrative" in out
    assert isinstance(out["gap_narratives"], list)

    loaded = get_audit_report_augmentation(
        run_id="run_model_aug_001",
        audit_root=tmp_path / "runs",
    )
    assert loaded["run_id"] == "run_model_aug_001"
