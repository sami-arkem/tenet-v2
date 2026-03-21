import json
from pathlib import Path

from src.workflow.workflow_runner import run_customer_evidence_pack


def test_run_customer_evidence_pack_smoke(tmp_path: Path, monkeypatch):
    import src.memory.audit_memory as audit_memory
    import src.memory.remediation_memory as remediation_memory
    import src.memory.trend_intelligence as trend_intelligence

    monkeypatch.setattr(audit_memory, "MEMORY_ROOT", tmp_path / "memory" / "snapshots")
    monkeypatch.setattr(remediation_memory, "REMEDIATION_SNAPSHOT_ROOT", tmp_path / "memory" / "remediation_snapshots")
    monkeypatch.setattr(trend_intelligence, "AUDIT_MEMORY_ROOT", tmp_path / "memory" / "snapshots")
    monkeypatch.setattr(trend_intelligence, "TREND_ROOT", tmp_path / "memory" / "trends")
    monkeypatch.setattr(trend_intelligence, "REMEDIATION_COMPARISON_ROOT", tmp_path / "memory" / "remediation_comparisons")

    pack_dir = tmp_path / "customer_pack"
    pack_dir.mkdir()

    (pack_dir / "audit_context.json").write_text(json.dumps({
        "audit_id": "pack-001",
        "entity_name": "Workflow Smoke Entity",
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US"],
        "entity_type": "payments_platform",
        "products": ["wallet"],
        "customer_types": ["consumer"],
        "source_families": ["regulations", "aml"],
        "query_terms": ["aml policy", "transaction monitoring"],
        "top_k": 2
    }), encoding="utf-8")

    result = run_customer_evidence_pack(pack_dir)
    assert Path(result["audit_output_path"]).exists()
    assert Path(result["workflow_result_path"]).exists()
    workflow_result = json.loads(Path(result["workflow_result_path"]).read_text(encoding="utf-8"))
    assert workflow_result["workflow_result_path"] == result["workflow_result_path"]
