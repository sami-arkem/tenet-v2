from __future__ import annotations

from core.model_manager import ModelManager, StubModelProvider
from core.model_tasks import (
    classify_document,
    explain_gap,
    extract_key_facts,
    write_executive_narrative,
)


class FailingProvider:
    def generate_json(self, **kwargs):
        raise RuntimeError("provider down")


def test_classify_document(tmp_path):
    mm = ModelManager(
        primary_provider=StubModelProvider(),
        fallback_provider=StubModelProvider(),
        log_root=tmp_path,
    )
    out = classify_document(
        filename="policy.txt",
        extracted_text="AML policy and procedure for transaction monitoring.",
        model_manager=mm,
    )
    assert out["category"] == "policy_document"
    assert "label" in out


def test_extract_key_facts(tmp_path):
    mm = ModelManager(
        primary_provider=StubModelProvider(),
        fallback_provider=StubModelProvider(),
        log_root=tmp_path,
    )
    out = extract_key_facts(
        category="policy_document",
        extracted_text="Line 1\nLine 2\nLine 3",
        model_manager=mm,
    )
    assert "facts" in out
    assert "label" in out


def test_gap_explanation_fallback(tmp_path):
    mm = ModelManager(
        primary_provider=FailingProvider(),
        fallback_provider=FailingProvider(),
        log_root=tmp_path,
    )
    out = explain_gap(
        finding={"finding_id": "f_001", "title": "Missing monitoring report"},
        requirement_text="Monitoring evidence must be retained.",
        model_manager=mm,
    )
    assert out["fallback_used"] is True
    assert "GAP:" in out["narrative"]


def test_executive_narrative_fallback(tmp_path):
    mm = ModelManager(
        primary_provider=FailingProvider(),
        fallback_provider=FailingProvider(),
        log_root=tmp_path,
    )
    out = write_executive_narrative(
        summary={"overall_posture": "AMBER", "deployment_decision": "CONDITIONALLY_APPROVED"},
        highlights=[{"finding_id": "f_001"}],
        model_manager=mm,
    )
    assert out["fallback_used"] is True
    assert "Deterministic audit posture" in out["narrative"]
