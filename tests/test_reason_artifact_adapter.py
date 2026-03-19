from __future__ import annotations

import json
from pathlib import Path

from core.reason_artifact_adapter import (
    build_canonical_execution_outcomes,
    load_reason_artifacts,
    write_canonical_execution_outcomes,
)


def _reason_artifacts() -> list[dict]:
    return [
        {
            "job_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "audit_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "tenant_id": "tenant-a",
            "audit_kind": "aml_periodic",
            "schedule_id": "sched-001",
            "deployment_decision": "CONDITIONALLY_APPROVED",
            "findings_count": 2,
            "missing_controls_count": 0,
            "missing_evidence_count": 0,
            "review_complete": True,
            "report_ready": True,
            "export_ready": True,
            "export_verified": True,
            "blocking_reasons": [],
        },
        {
            "job_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "audit_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "tenant_id": "tenant-b",
            "audit_kind": "vendor_risk_review",
            "schedule_id": "sched-010",
            "deployment_decision": "BLOCKED",
            "findings": [{"id": "f1"}],
            "missing_controls": [{"id": "c1"}],
            "missing_evidence": [{"id": "e1"}],
            "review_complete": False,
            "report_ready": False,
            "export_ready": False,
            "export_verified": False,
            "blocking_reasons": ["evidence:missing_required_pack"],
        },
    ]


def test_build_canonical_execution_outcomes() -> None:
    artifact = build_canonical_execution_outcomes(_reason_artifacts())

    assert artifact.total_jobs_seen == 2
    assert artifact.total_completed == 1
    assert artifact.total_failed == 1
    assert artifact.total_blocked == 0
    assert artifact.source_contract == "canonical_reason_artifact_v1"

    first = artifact.job_outcomes["tenant-a:aml_periodic:sched-001:2026-02-15"]
    second = artifact.job_outcomes["tenant-b:vendor_risk_review:sched-010:2026-02-20"]

    assert first["release_ready"] is True
    assert first["verdict_status"] == "CONDITIONALLY_APPROVED"

    assert second["release_ready"] is False
    assert "controls:missing:1" in second["blocking_reasons"]
    assert "evidence:missing:1" in second["blocking_reasons"]
    assert "review:incomplete" in second["blocking_reasons"]
    assert "export_surface:export_not_verified" in second["blocking_reasons"]


def test_missing_required_fields_raise() -> None:
    try:
        build_canonical_execution_outcomes([{"job_id": "j1"}])
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "tenant_id" in str(exc) or "audit_kind" in str(exc)


def test_loaders_and_writer(tmp_path: Path) -> None:
    json_path = tmp_path / "reason_artifacts.json"
    jsonl_path = tmp_path / "reason_artifacts.jsonl"
    output_path = tmp_path / "execution_outcomes.json"

    json_path.write_text(json.dumps({"artifacts": _reason_artifacts()}) + "\n", encoding="utf-8")
    jsonl_path.write_text(
        "\n".join(json.dumps(row) for row in reversed(_reason_artifacts())) + "\n",
        encoding="utf-8",
    )

    loaded_json = load_reason_artifacts(json_path)
    loaded_jsonl = load_reason_artifacts(jsonl_path)

    assert loaded_json[0]["job_id"] == "tenant-a:aml_periodic:sched-001:2026-02-15"
    assert loaded_jsonl[0]["job_id"] == "tenant-a:aml_periodic:sched-001:2026-02-15"

    artifact = build_canonical_execution_outcomes(loaded_json)
    write_canonical_execution_outcomes(output_path, artifact)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["total_jobs_seen"] == 2
    assert payload["source_contract"] == "canonical_reason_artifact_v1"
