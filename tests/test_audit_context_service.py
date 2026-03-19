from __future__ import annotations

from pathlib import Path

from core.audit_context_service import (
    build_default_audit_questions,
    build_retrieval_grounded_context_pack,
    get_context_pack,
)
from core.evidence_ingestion_service import ingest_evidence_file
from core.evidence_pack_service import create_evidence_pack
from core.evidence_processing_service import process_all_evidence_for_pack
from core.retrieval_service import build_pack_retrieval_index


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


def test_build_default_audit_questions(tmp_path: Path):
    pack = create_evidence_pack(
        name="Acme AML Pack",
        created_by="sami",
        manifest=make_manifest(),
        pack_root=tmp_path / "packs",
    )

    questions = build_default_audit_questions(
        pack_id=pack["pack_id"],
        pack_root=tmp_path / "packs",
    )
    assert len(questions) >= 3
    assert any("transaction monitoring" in q.lower() for q in questions)


def test_build_and_get_context_pack(tmp_path: Path):
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
    build_pack_retrieval_index(pack_id=pack["pack_id"], pack_root=tmp_path / "packs")

    ctx = build_retrieval_grounded_context_pack(
        pack_id=pack["pack_id"],
        top_k_per_question=3,
        pack_root=tmp_path / "packs",
    )
    assert ctx["deterministic_authoritative"] is True
    assert ctx["question_count"] >= 1
    assert ctx["selected_chunk_count"] >= 1
    assert len(ctx["questions"]) >= 1

    loaded = get_context_pack(pack_id=pack["pack_id"], pack_root=tmp_path / "packs")
    assert loaded["pack_id"] == pack["pack_id"]
    assert loaded["selected_chunk_count"] == ctx["selected_chunk_count"]
