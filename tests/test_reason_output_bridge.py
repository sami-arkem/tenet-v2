from __future__ import annotations

import json
from pathlib import Path

from core.reason_output_bridge import (
    build_canonical_reason_artifact_bundle,
    load_reason_outputs,
    write_canonical_reason_artifact_bundle,
)


def _raw_reason_outputs() -> list[dict]:
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


def test_build_bundle_from_raw_reason_output() -> None:
    bundle = build_canonical_reason_artifact_bundle(_raw_reason_outputs())

    assert bundle.total_artifacts == 2
    assert bundle.source_contract == "reason_output_v1_to_canonical_reason_artifact_v1"

    first = bundle.canonical_reason_artifacts[0]
    second = bundle.canonical_reason_artifacts[1]

    assert first.job_id == "tenant-a:aml_periodic:sched-001:2026-02-15"
    assert first.blocking_reasons == []

    assert second.findings_count == 1
    assert second.missing_controls_count == 1
    assert second.missing_evidence_count == 1
    assert "controls:missing:1" in second.blocking_reasons
    assert "evidence:missing:1" in second.blocking_reasons
    assert "review:incomplete" in second.blocking_reasons


def test_missing_required_fields_raise() -> None:
    try:
        build_canonical_reason_artifact_bundle([{"job_id": "x"}])
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "tenant_id" in str(exc) or "audit_kind" in str(exc)


def test_loaders_and_writer(tmp_path: Path) -> None:
    json_path = tmp_path / "reason_output.json"
    jsonl_path = tmp_path / "reason_output.jsonl"
    output_path = tmp_path / "canonical_reason_artifacts.json"

    json_path.write_text(json.dumps({"results": _raw_reason_outputs()}) + "\n", encoding="utf-8")
    jsonl_path.write_text(
        "\n".join(json.dumps(row) for row in reversed(_raw_reason_outputs())) + "\n",
        encoding="utf-8",
    )

    loaded_json = load_reason_outputs(json_path)
    loaded_jsonl = load_reason_outputs(jsonl_path)

    assert loaded_json[0]["job_id"] == "tenant-a:aml_periodic:sched-001:2026-02-15"
    assert loaded_jsonl[0]["job_id"] == "tenant-a:aml_periodic:sched-001:2026-02-15"

    bundle = build_canonical_reason_artifact_bundle(loaded_json)
    write_canonical_reason_artifact_bundle(output_path, bundle)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["total_artifacts"] == 2
