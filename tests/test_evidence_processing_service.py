from __future__ import annotations

from pathlib import Path

from core.evidence_ingestion_service import ingest_evidence_file
from core.evidence_pack_service import create_evidence_pack
from core.evidence_processing_service import (
    build_corpus_readiness,
    process_all_evidence_for_pack,
    process_evidence_item,
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
        "controls": [],
        "evidence_catalog": [],
    }


def test_process_single_text_item(tmp_path: Path):
    pack = create_evidence_pack(
        name="Acme AML Pack",
        created_by="sami",
        manifest=make_manifest(),
        pack_root=tmp_path / "packs",
    )

    item = ingest_evidence_file(
        pack_id=pack["pack_id"],
        filename="monitoring_policy.txt",
        data=b"Transaction monitoring policy for AML controls.\n",
        title="Monitoring Policy",
        source_type="policy_document",
        citation="monitoring_policy.txt#L1-L1",
        pack_root=tmp_path / "packs",
        evidence_root=tmp_path / "blobs",
    )

    processed = process_evidence_item(
        pack_id=pack["pack_id"],
        evidence_id=item["evidence_id"],
        pack_root=tmp_path / "packs",
    )

    assert processed["processing_status"] == "READY"
    assert processed["classification"]["confidence"] == "HIGH"
    assert Path(processed["extracted_text_path"]).exists()
    assert Path(processed["classification_path"]).exists()
    assert Path(processed["key_facts_path"]).exists()


def test_process_all_and_readiness(tmp_path: Path):
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
    ingest_evidence_file(
        pack_id=pack["pack_id"],
        filename="owner_matrix.json",
        data=b'{"owner":"compliance"}',
        title="Owner Matrix",
        source_type="owner_matrix",
        citation="owner_matrix.json#L1-L1",
        pack_root=tmp_path / "packs",
        evidence_root=tmp_path / "blobs",
    )

    out = process_all_evidence_for_pack(
        pack_id=pack["pack_id"],
        pack_root=tmp_path / "packs",
    )
    assert out["processed_count"] == 2
    assert out["failure_count"] == 0
    assert out["readiness"]["corpus_ready"] is True
    assert out["readiness"]["ready_count"] == 2

    readiness = build_corpus_readiness(
        pack_id=pack["pack_id"],
        pack_root=tmp_path / "packs",
    )
    assert readiness["event"] == "CORPUS_READY"
