from __future__ import annotations

import json
from pathlib import Path

from core.immutable_release_package import (
    build_immutable_release_package,
    load_artifact,
    write_immutable_release_package,
)


def _pass_finalize_decision() -> dict:
    return {
        "schema_version": "1.0",
        "finalize_status": "PASS",
        "finalize_ready": True,
        "release_package_created": True,
        "release_package_path": "/tmp/release_package.json",
        "blocking_reasons": [],
        "payload_hash": "pass",
    }


def _blocked_finalize_decision() -> dict:
    return {
        "schema_version": "1.0",
        "finalize_status": "BLOCKED",
        "finalize_ready": False,
        "release_package_created": False,
        "release_package_path": None,
        "blocking_reasons": ["audit_execution:execution_not_complete:1"],
        "payload_hash": "blocked",
    }


def test_build_release_package_passes_only_when_finalize_passes(tmp_path: Path) -> None:
    file_a = tmp_path / "a.json"
    file_b = tmp_path / "b.json"
    file_a.write_text('{"a":1}\n', encoding="utf-8")
    file_b.write_text('{"b":2}\n', encoding="utf-8")

    artifact = build_immutable_release_package(
        finalize_decision=_pass_finalize_decision(),
        files_to_include=[file_b, file_a],
        manifest_path=tmp_path / "immutable_release_package.json",
    )

    assert artifact.package_status == "PASS"
    assert artifact.package_ready is True
    assert [x.path for x in artifact.included_files] == [str(file_a), str(file_b)]
    assert artifact.blocking_reasons == []


def test_build_release_package_blocks_when_finalize_blocked(tmp_path: Path) -> None:
    file_a = tmp_path / "a.json"
    file_a.write_text('{"a":1}\n', encoding="utf-8")

    artifact = build_immutable_release_package(
        finalize_decision=_blocked_finalize_decision(),
        files_to_include=[file_a],
        manifest_path=tmp_path / "immutable_release_package.json",
    )

    assert artifact.package_status == "BLOCKED"
    assert artifact.package_ready is False
    assert artifact.included_files == []
    assert "audit_execution:execution_not_complete:1" in artifact.blocking_reasons


def test_missing_input_file_raises_on_pass(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    try:
        build_immutable_release_package(
            finalize_decision=_pass_finalize_decision(),
            files_to_include=[missing],
            manifest_path=tmp_path / "immutable_release_package.json",
        )
        raise AssertionError("expected FileNotFoundError")
    except FileNotFoundError:
        pass


def test_writer_and_loader(tmp_path: Path) -> None:
    file_a = tmp_path / "a.json"
    file_a.write_text('{"a":1}\n', encoding="utf-8")

    artifact = build_immutable_release_package(
        finalize_decision=_pass_finalize_decision(),
        files_to_include=[file_a],
        manifest_path=tmp_path / "immutable_release_package.json",
    )

    output_path = tmp_path / "immutable_release_package.json"
    write_immutable_release_package(output_path, artifact)
    payload = load_artifact(output_path)

    assert payload["package_status"] == "PASS"
    assert payload["package_ready"] is True
    assert len(payload["included_files"]) == 1
