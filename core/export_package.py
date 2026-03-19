from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.audit_pipeline import build_execution_bundle, result_to_snapshot, run_audit_from_payload
from core.report_renderer import render_report_bundle


SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _require_non_empty_str(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _safe_name(value: str) -> str:
    value = _require_non_empty_str(value, "name")
    safe = SAFE_NAME_RE.sub("_", value.strip())
    safe = safe.strip("._")
    if not safe:
        raise ValueError("name becomes empty after sanitization")
    return safe


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=False) + "\n")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


@dataclass(frozen=True)
class ExportPackagePaths:
    package_dir: Path
    report_markdown_path: Path
    report_bundle_path: Path
    report_pack_path: Path
    deterministic_result_path: Path
    snapshot_path: Path
    input_payload_path: Path
    audit_context_pack_path: Path
    control_coverage_path: Path
    audit_dossier_path: Path
    release_gate_path: Path
    composed_report_bundle_path: Path
    manifest_path: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "package_dir": str(self.package_dir),
            "report_markdown_path": str(self.report_markdown_path),
            "report_bundle_path": str(self.report_bundle_path),
            "report_pack_path": str(self.report_pack_path),
            "deterministic_result_path": str(self.deterministic_result_path),
            "snapshot_path": str(self.snapshot_path),
            "input_payload_path": str(self.input_payload_path),
            "audit_context_pack_path": str(self.audit_context_pack_path),
            "control_coverage_path": str(self.control_coverage_path),
            "audit_dossier_path": str(self.audit_dossier_path),
            "release_gate_path": str(self.release_gate_path),
            "composed_report_bundle_path": str(self.composed_report_bundle_path),
            "manifest_path": str(self.manifest_path),
        }


def build_package_paths(base_dir: Path, package_name: str) -> ExportPackagePaths:
    package_dir = base_dir / _safe_name(package_name)
    return ExportPackagePaths(
        package_dir=package_dir,
        report_markdown_path=package_dir / "report.md",
        report_bundle_path=package_dir / "report_bundle.json",
        report_pack_path=package_dir / "report_pack.json",
        deterministic_result_path=package_dir / "deterministic_audit_result.json",
        snapshot_path=package_dir / "snapshot.json",
        input_payload_path=package_dir / "input_payload.json",
        audit_context_pack_path=package_dir / "audit_context_pack.json",
        control_coverage_path=package_dir / "control_coverage.json",
        audit_dossier_path=package_dir / "audit_dossier.json",
        release_gate_path=package_dir / "release_gate.json",
        composed_report_bundle_path=package_dir / "composed_report_bundle.json",
        manifest_path=package_dir / "manifest.json",
    )


def _resolve_report_bundle(
    *,
    payload: dict[str, Any],
    default_report_bundle: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    composed = payload.get("composed_report_bundle")
    if isinstance(composed, dict) and isinstance(composed.get("markdown"), str) and composed["markdown"].strip():
        return composed, "composed_report_bundle"
    return default_report_bundle, "deterministic_report_bundle"


def build_export_manifest(
    *,
    package_paths: ExportPackagePaths,
    run_id: str,
    package_version: str,
    payload: dict[str, Any],
    deterministic_result: dict[str, Any],
    report_pack: dict[str, Any],
    report_bundle: dict[str, Any],
    snapshot: dict[str, Any],
    report_source: str,
) -> dict[str, Any]:
    package_dir = package_paths.package_dir
    files = []
    for path in [
        package_paths.input_payload_path,
        package_paths.audit_context_pack_path,
        package_paths.control_coverage_path,
        package_paths.audit_dossier_path,
        package_paths.release_gate_path,
        package_paths.composed_report_bundle_path,
        package_paths.deterministic_result_path,
        package_paths.report_pack_path,
        package_paths.report_bundle_path,
        package_paths.snapshot_path,
        package_paths.report_markdown_path,
    ]:
        if not path.exists():
            raise ValueError(f"missing export file for manifest generation: {path}")
        files.append(
            {
                "path": _relative(path, package_dir),
                "sha256": _sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )

    return {
        "package_version": package_version,
        "run_id": run_id,
        "generated_from_canonical_runtime": True,
        "historical_context_is_non_authoritative": bool(
            deterministic_result.get("scope", {}).get("historical_context_is_non_authoritative", False)
        ),
        "deterministic_current_audit_truth_only": bool(
            deterministic_result.get("scope", {}).get("deterministic_current_audit_truth_only", False)
        ),
        "deployment_decision": snapshot.get("summary", {}).get("deployment_decision"),
        "overall_posture": snapshot.get("summary", {}).get("overall_posture"),
        "finding_count": len(deterministic_result.get("findings", [])),
        "remediation_item_count": len(deterministic_result.get("remediation_items", [])),
        "input_payload_sha256": _sha256_bytes(json.dumps(payload, sort_keys=True).encode("utf-8")),
        "audit_context_pack_present": isinstance(payload.get("audit_context_pack"), dict),
        "control_coverage_present": isinstance(payload.get("control_coverage_matrix"), dict),
        "audit_dossier_present": isinstance(payload.get("audit_dossier"), dict),
        "release_gate_present": isinstance(payload.get("release_gate"), dict),
        "composed_report_bundle_present": isinstance(payload.get("composed_report_bundle"), dict),
        "report_source": report_source,
        "report_pack_sha256": _sha256_bytes(json.dumps(report_pack, sort_keys=True).encode("utf-8")),
        "report_bundle_sha256": _sha256_bytes(json.dumps(report_bundle, sort_keys=True).encode("utf-8")),
        "snapshot_sha256": _sha256_bytes(json.dumps(snapshot, sort_keys=True).encode("utf-8")),
        "files": files,
    }


def validate_export_manifest(manifest: dict[str, Any]) -> None:
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be an object")
    if manifest.get("generated_from_canonical_runtime") is not True:
        raise ValueError("manifest.generated_from_canonical_runtime must be true")
    if manifest.get("historical_context_is_non_authoritative") is not True:
        raise ValueError("manifest.historical_context_is_non_authoritative must be true")
    if manifest.get("deterministic_current_audit_truth_only") is not True:
        raise ValueError("manifest.deterministic_current_audit_truth_only must be true")

    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("manifest.run_id must be non-empty string")

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("manifest.files must be non-empty list")

    report_source = manifest.get("report_source")
    if report_source not in {"deterministic_report_bundle", "composed_report_bundle"}:
        raise ValueError("manifest.report_source must be deterministic_report_bundle or composed_report_bundle")

    for idx, row in enumerate(files):
        if not isinstance(row, dict):
            raise ValueError(f"manifest.files[{idx}] must be object")
        if not isinstance(row.get("path"), str) or not row["path"].strip():
            raise ValueError(f"manifest.files[{idx}].path must be non-empty string")
        sha = row.get("sha256")
        if not isinstance(sha, str) or len(sha) != 64:
            raise ValueError(f"manifest.files[{idx}].sha256 must be 64-char hex string")
        size = row.get("size_bytes")
        if not isinstance(size, int) or size < 0:
            raise ValueError(f"manifest.files[{idx}].size_bytes must be non-negative int")


def verify_export_package(package_dir: Path) -> dict[str, Any]:
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"manifest missing: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_export_manifest(manifest)

    verification_rows = []
    all_ok = True
    for row in manifest["files"]:
        rel = row["path"]
        path = package_dir / rel
        exists = path.exists()
        sha_ok = False
        size_ok = False
        if exists:
            sha_ok = _sha256_file(path) == row["sha256"]
            size_ok = path.stat().st_size == row["size_bytes"]
        ok = exists and sha_ok and size_ok
        if not ok:
            all_ok = False
        verification_rows.append(
            {
                "path": rel,
                "exists": exists,
                "sha_ok": sha_ok,
                "size_ok": size_ok,
                "ok": ok,
            }
        )

    return {
        "package_dir": str(package_dir),
        "run_id": manifest["run_id"],
        "all_ok": all_ok,
        "files": verification_rows,
    }


def export_audit_package(
    *,
    payload: dict[str, Any],
    export_root: Path,
    package_name: str | None = None,
    package_version: str = "v1",
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")

    result = run_audit_from_payload(payload)
    execution_bundle = build_execution_bundle(payload)
    default_report_bundle = render_report_bundle(result)
    chosen_report_bundle, report_source = _resolve_report_bundle(
        payload=payload,
        default_report_bundle=default_report_bundle,
    )
    snapshot = result_to_snapshot(result)

    run_id = result.run_id
    resolved_package_name = package_name or f"audit_package_{run_id}"
    package_paths = build_package_paths(export_root, resolved_package_name)
    package_paths.package_dir.mkdir(parents=True, exist_ok=True)

    _atomic_write_json(package_paths.input_payload_path, payload)
    _atomic_write_json(package_paths.audit_context_pack_path, payload.get("audit_context_pack", {}))
    _atomic_write_json(package_paths.control_coverage_path, payload.get("control_coverage_matrix", {}))
    _atomic_write_json(package_paths.audit_dossier_path, payload.get("audit_dossier", {}))
    _atomic_write_json(package_paths.release_gate_path, payload.get("release_gate", {}))
    _atomic_write_json(package_paths.composed_report_bundle_path, payload.get("composed_report_bundle", {}))
    _atomic_write_json(package_paths.deterministic_result_path, execution_bundle["deterministic_audit_result"])
    _atomic_write_json(package_paths.report_pack_path, execution_bundle["report_pack"])
    _atomic_write_json(package_paths.report_bundle_path, chosen_report_bundle)
    _atomic_write_json(package_paths.snapshot_path, snapshot)
    _atomic_write_text(package_paths.report_markdown_path, chosen_report_bundle["markdown"].rstrip() + "\n")

    manifest = build_export_manifest(
        package_paths=package_paths,
        run_id=run_id,
        package_version=package_version,
        payload=payload,
        deterministic_result=execution_bundle["deterministic_audit_result"],
        report_pack=execution_bundle["report_pack"],
        report_bundle=chosen_report_bundle,
        snapshot=snapshot,
        report_source=report_source,
    )
    validate_export_manifest(manifest)
    _atomic_write_json(package_paths.manifest_path, manifest)
    verification = verify_export_package(package_paths.package_dir)

    return {
        "run_id": run_id,
        "package_paths": package_paths.to_dict(),
        "manifest": manifest,
        "verification": verification,
        "topline": execution_bundle["topline"],
    }
