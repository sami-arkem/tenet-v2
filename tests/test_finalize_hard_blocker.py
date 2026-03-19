from __future__ import annotations

import json
from pathlib import Path

from core.finalize_hard_blocker import (
    build_finalize_decision,
    load_artifact,
    write_finalize_decision,
)


def _blocked_finalize_artifact() -> dict:
    return {
        "schema_version": "1.0",
        "finalize_status": "BLOCKED",
        "finalize_ready": False,
        "blocking_reasons": [
            "release_surface:audit_runner:open_jobs:2",
            "audit_execution:execution_not_complete:1",
        ],
        "payload_hash": "blocked",
    }


def _pass_finalize_artifact() -> dict:
    return {
        "schema_version": "1.0",
        "finalize_status": "PASS",
        "finalize_ready": True,
        "blocking_reasons": [],
        "payload_hash": "pass",
    }


def test_finalize_decision_blocks_when_artifact_blocked() -> None:
    decision = build_finalize_decision(
        finalize_release_artifact=_blocked_finalize_artifact(),
        release_package_path="state/finalize/release_package.json",
    )

    assert decision.finalize_status == "BLOCKED"
    assert decision.finalize_ready is False
    assert decision.release_package_created is False
    assert decision.release_package_path is None
    assert "audit_execution:execution_not_complete:1" in decision.blocking_reasons


def test_finalize_decision_passes_only_on_pass_artifact() -> None:
    decision = build_finalize_decision(
        finalize_release_artifact=_pass_finalize_artifact(),
        release_package_path="state/finalize/release_package.json",
    )

    assert decision.finalize_status == "PASS"
    assert decision.finalize_ready is True
    assert decision.release_package_created is True
    assert decision.release_package_path == "state/finalize/release_package.json"
    assert decision.blocking_reasons == []


def test_writer_and_loader(tmp_path: Path) -> None:
    output_path = tmp_path / "finalize_decision.json"
    decision = build_finalize_decision(
        finalize_release_artifact=_pass_finalize_artifact(),
        release_package_path="state/finalize/release_package.json",
    )
    write_finalize_decision(output_path, decision)
    payload = load_artifact(output_path)

    assert payload["finalize_status"] == "PASS"
    assert payload["release_package_created"] is True
