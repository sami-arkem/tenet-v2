from __future__ import annotations

from pathlib import Path

from core.evidence_ingestion_service import ingest_evidence_file
from core.evidence_pack_service import create_evidence_pack
from core.evidence_processing_service import process_all_evidence_for_pack
from core.retrieval_service import (
    build_audit_context_pack,
    build_pack_retrieval_index,
    load_pack_retrieval_index,
    search_pack_corpus,
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


def test_build_and_search_retrieval_index(tmp_path: Path):
    pack = create_evidence_pack(
        name="Acme AML Pack",
        created_by="sami",
        manifest=make_manifest(),
        pack_root=tmp_path / "packs",
    )

    ingest_evidence_file(
        pack_id=pack["pack_id"],
        filename="policy.txt",
        data=b"AML transaction monitoring policy and escalation procedure.",
        title="Monitoring Policy",
        source_type="policy_document",
        citation="policy.txt#L1-L1",
        pack_root=tmp_path / "packs",
        evidence_root=tmp_path / "blobs",
    )
    ingest_evidence_file(
        pack_id=pack["pack_id"],
        filename="screening.txt",
        data=b"Sanctions screening alert handling and OFAC escalation workflow.",
        title="Screening Alerts",
        source_type="screening_alert_log",
        citation="screening.txt#L1-L1",
        pack_root=tmp_path / "packs",
        evidence_root=tmp_path / "blobs",
    )

    process_all_evidence_for_pack(pack_id=pack["pack_id"], pack_root=tmp_path / "packs")
    built = build_pack_retrieval_index(pack_id=pack["pack_id"], pack_root=tmp_path / "packs")
    assert built["document_count"] == 2
    assert built["chunk_count"] >= 2

    loaded = load_pack_retrieval_index(pack_id=pack["pack_id"], pack_root=tmp_path / "packs")
    assert loaded["pack_id"] == pack["pack_id"]

    result = search_pack_corpus(
        pack_id=pack["pack_id"],
        query="transaction monitoring escalation",
        top_k=5,
        pack_root=tmp_path / "packs",
    )
    assert result["result_count"] >= 1
    assert any("policy" in (row["filename"] or "") for row in result["results"])


def test_build_audit_context_pack(tmp_path: Path):
    pack = create_evidence_pack(
        name="Acme AML Pack",
        created_by="sami",
        manifest=make_manifest(),
        pack_root=tmp_path / "packs",
    )

    ingest_evidence_file(
        pack_id=pack["pack_id"],
        filename="policy.txt",
        data=b"AML transaction monitoring policy and escalation procedure.",
        title="Monitoring Policy",
        source_type="policy_document",
        citation="policy.txt#L1-L1",
        pack_root=tmp_path / "packs",
        evidence_root=tmp_path / "blobs",
    )
    process_all_evidence_for_pack(pack_id=pack["pack_id"], pack_root=tmp_path / "packs")
    build_pack_retrieval_index(pack_id=pack["pack_id"], pack_root=tmp_path / "packs")

    ctx = build_audit_context_pack(
        pack_id=pack["pack_id"],
        audit_questions=[
            "What evidence supports transaction monitoring?",
            "What evidence supports escalation procedures?",
        ],
        top_k_per_question=3,
        pack_root=tmp_path / "packs",
    )
    assert ctx["question_count"] == 2
    assert ctx["selected_chunk_count"] >= 1
    assert len(ctx["questions"]) == 2
