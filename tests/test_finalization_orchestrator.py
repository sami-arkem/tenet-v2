from __future__ import annotations

import json
from pathlib import Path

from core.finalization_orchestrator import (
    build_finalization_receipt,
    load_artifact,
    write_finalization_receipt,
)


def _finalize_decision_pass() -> dict:
    return {
        "schema_version": "1.0",
        "finalize_status": "PASS",
        "finalize_ready": True,
        "release_package_created": True,
        "release_package_path": "/tmp/tenet_release_package.json",
        "blocking_reasons": [],
        "payload_hash": "finalize-pass",
    }


def _finalize_decision_blocked() -> dict:
    return {
        "schema_version": "1.0",
        "finalize_status": "BLOCKED",
        "finalize_ready": False,
        "release_package_created": False,
        "release_package_path": None,
        "blocking_reasons": ["audit_execution:execution_not_complete:1"],
        "payload_hash": "finalize-blocked",
    }


def _immutable_package_pass() -> dict:
    return {
        "schema_version": "1.0",
        "package_status": "PASS",
        "package_ready": True,
        "finalize_status": "PASS",
        "included_files": [
            {"path": "/tmp/a.json", "sha256": "aaa"},
            {"path": "/tmp/b.json", "sha256": "bbb"},
        ],
        "manifest_path": "/tmp/immutable_release_package.json",
        "blocking_reasons": [],
        "payload_hash": "package-pass",
    }


def _immutable_package_blocked() -> dict:
    return {
        "schema_version": "1.0",
        "package_status": "BLOCKED",
        "package_ready": False,
        "finalize_status": "BLOCKED",
        "included_files": [],
        "manifest_path": "/tmp/immutable_release_package.json",
        "blocking_reasons": ["audit_execution:execution_not_complete:1"],
        "payload_hash": "package-blocked",
    }


def test_finalization_receipt_passes_only_when_both_pass() -> None:
    receipt = build_finalization_receipt(
        finalize_decision=_finalize_decision_pass(),
        immutable_release_package=_immutable_package_pass(),
    )

    assert receipt.finalization_status == "PASS"
    assert receipt.finalization_ready is True
    assert len(receipt.included_files) == 2
    assert receipt.blocking_reasons == []


def test_finalization_receipt_blocks_when_finalize_blocked() -> None:
    receipt = build_finalization_receipt(
        finalize_decision=_finalize_decision_blocked(),
        immutable_release_package=_immutable_package_pass(),
    )

    assert receipt.finalization_status == "BLOCKED"
    assert receipt.finalization_ready is False
    assert "finalize_decision:audit_execution:execution_not_complete:1" in receipt.blocking_reasons


def test_finalization_receipt_blocks_when_package_blocked() -> None:
    receipt = build_finalization_receipt(
        finalize_decision=_finalize_decision_pass(),
        immutable_release_package=_immutable_package_blocked(),
    )

    assert receipt.finalization_status == "BLOCKED"
    assert receipt.finalization_ready is False
    assert "immutable_release_package:audit_execution:execution_not_complete:1" in receipt.blocking_reasons


def test_writer_and_loader(tmp_path: Path) -> None:
    path = tmp_path / "finalization_receipt.json"
    receipt = build_finalization_receipt(
        finalize_decision=_finalize_decision_pass(),
        immutable_release_package=_immutable_package_pass(),
    )
    write_finalization_receipt(path, receipt)
    payload = load_artifact(path)

    assert payload["finalization_status"] == "PASS"
    assert payload["finalization_ready"] is True
