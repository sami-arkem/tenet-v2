from __future__ import annotations

import json
from pathlib import Path

from core.reason_result_outcome_emitter import (
    build_execution_outcomes,
    load_reason_results,
    write_execution_outcomes,
)


def _reason_results() -> list[dict]:
    return [
        {
            "job_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "audit_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "run_status": "COMPLETED",
            "execution_status": "COMPLETED",
            "verdict_status": "CONDITIONALLY_APPROVED",
            "report_ready": True,
            "export_ready": True,
            "blocking_reasons": [],
        },
        {
            "job_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "audit_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "run_status": "FAILED",
            "execution_status": "BLOCKED",
            "verdict_status": "BLOCKED",
            "report_ready": False,
            "export_ready": False,
            "blocking_reasons": ["evidence:missing_required_pack"],
        },
    ]


def test_build_execution_outcomes_maps_reason_results_correctly() -> None:
    artifact = build_execution_outcomes(_reason_results())

    assert artifact.total_jobs_seen == 2
    assert artifact.total_completed == 1
    assert artifact.total_failed == 1  # run_status=FAILED counts as failed
    assert artifact.total_blocked == 0  # blocked only if not failed and not completed

    first = artifact.job_outcomes["tenant-a:aml_periodic:sched-001:2026-02-15"]
    second = artifact.job_outcomes["tenant-b:vendor_risk_review:sched-010:2026-02-20"]

    assert first["release_ready"] is True
    assert first["blocking_reasons"] == []

    assert second["release_ready"] is False
    assert "evidence:missing_required_pack" in second["blocking_reasons"]
    assert "report_surface:report_not_ready" in second["blocking_reasons"]
    assert "export_surface:export_not_ready" in second["blocking_reasons"]


def test_missing_statuses_are_derived_deterministically() -> None:
    artifact = build_execution_outcomes([
        {
            "job_id": "j1",
            "audit_id": "j1",
            "report_ready": False,
            "export_ready": False,
            "blocking_reasons": ["evidence:missing_required_pack"],
        }
    ])

    outcome = artifact.job_outcomes["j1"]
    assert outcome["run_status"] == "FAILED"
    assert outcome["execution_status"] == "BLOCKED"
    assert outcome["verdict_status"] == "BLOCKED"


def test_loaders_and_writer(tmp_path: Path) -> None:
    json_path = tmp_path / "reason_results.json"
    jsonl_path = tmp_path / "reason_results.jsonl"
    output_path = tmp_path / "execution_outcomes.json"

    json_path.write_text(json.dumps({"results": _reason_results()}) + "\n", encoding="utf-8")
    jsonl_path.write_text(
        "\n".join(json.dumps(row) for row in reversed(_reason_results())) + "\n",
        encoding="utf-8",
    )

    loaded_json = load_reason_results(json_path)
    loaded_jsonl = load_reason_results(jsonl_path)

    assert loaded_json[0]["job_id"] == "tenant-a:aml_periodic:sched-001:2026-02-15"
    assert loaded_jsonl[0]["job_id"] == "tenant-a:aml_periodic:sched-001:2026-02-15"

    artifact = build_execution_outcomes(loaded_json)
    write_execution_outcomes(output_path, artifact)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["total_jobs_seen"] == 2
