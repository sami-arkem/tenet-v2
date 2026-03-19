import json
from pathlib import Path

from src.workflow.evidence_pack_loader import load_evidence_pack, EvidencePackError


def test_load_evidence_pack_ok(tmp_path: Path):
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "audit_context.json").write_text(json.dumps({
        "audit_id": "pack-001",
        "entity_name": "Pack Entity",
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US"],
        "source_families": ["regulations", "aml"],
        "query_terms": ["aml policy"],
        "top_k": 5
    }), encoding="utf-8")

    pack = load_evidence_pack(pack_dir)
    assert pack["audit_context"]["audit_id"] == "pack-001"


def test_load_evidence_pack_missing_field(tmp_path: Path):
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "audit_context.json").write_text(json.dumps({
        "audit_id": "pack-001"
    }), encoding="utf-8")

    try:
        load_evidence_pack(pack_dir)
    except EvidencePackError as exc:
        assert "Missing required audit_context fields" in str(exc)
    else:
        raise AssertionError("Expected EvidencePackError")
