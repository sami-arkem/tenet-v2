from __future__ import annotations

from pathlib import Path

from core.evidence_ingestion_service import ingest_evidence_file, list_evidence_items
from core.evidence_pack_service import create_evidence_pack, get_evidence_pack


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


def test_ingest_text_file_updates_pack_manifest(tmp_path: Path):
    pack = create_evidence_pack(
        name="Acme AML Pack",
        created_by="sami",
        manifest=make_manifest(),
        pack_root=tmp_path / "packs",
    )

    row = ingest_evidence_file(
        pack_id=pack["pack_id"],
        filename="monitoring_policy.txt",
        data=b"real policy text\n",
        title="Monitoring Policy",
        source_type="policy_document",
        citation="monitoring_policy.txt#L1-L1",
        pack_root=tmp_path / "packs",
        evidence_root=tmp_path / "blobs",
    )

    assert row["processing_status"] == "UPLOADED"
    assert row["detected_mime"] == "text/plain"
    assert Path(row["storage_path"]).exists()

    items = list_evidence_items(pack["pack_id"], pack_root=tmp_path / "packs")
    assert len(items) == 1
    assert items[0]["evidence_id"] == row["evidence_id"]

    loaded = get_evidence_pack(pack["pack_id"], pack_root=tmp_path / "packs")
    assert len(loaded["manifest"]["evidence_catalog"]) == 1
    assert loaded["manifest"]["evidence_catalog"][0]["evidence_id"] == row["evidence_id"]


def test_ingest_json_file(tmp_path: Path):
    pack = create_evidence_pack(
        name="Acme AML Pack",
        created_by="sami",
        manifest=make_manifest(),
        pack_root=tmp_path / "packs",
    )

    row = ingest_evidence_file(
        pack_id=pack["pack_id"],
        filename="owner_matrix.json",
        data=b'{"owner":"compliance"}',
        title="Owner Matrix",
        source_type="owner_matrix",
        citation="owner_matrix.json#L1-L1",
        pack_root=tmp_path / "packs",
        evidence_root=tmp_path / "blobs",
    )

    assert row["detected_mime"] == "application/json"
    assert row["ocr_status"] == "NOT_REQUIRED"
