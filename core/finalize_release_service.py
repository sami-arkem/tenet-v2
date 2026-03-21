from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.audit_dossier_service import build_audit_dossier
from core.control_coverage_service import build_control_coverage_matrix
from core.export_package import export_audit_package
from core.release_gate_service import build_release_gate
from core.report_composer import build_composed_report_bundle

DEFAULT_AUDIT_ROOT = Path("artifacts") / "audit_runs"
DEFAULT_RELEASE_ROOT = Path("artifacts") / "released_audits"


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


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


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _audit_run_dir(run_id: str, audit_root: Path = DEFAULT_AUDIT_ROOT) -> Path:
    return audit_root / _require_non_empty_str(run_id, "run_id")


def _detail_path(run_id: str, audit_root: Path = DEFAULT_AUDIT_ROOT) -> Path:
    return _audit_run_dir(run_id, audit_root) / "detail.json"


def _finalization_path(run_id: str, audit_root: Path = DEFAULT_AUDIT_ROOT) -> Path:
    return _audit_run_dir(run_id, audit_root) / "release_finalization.json"


def _load_detail(run_id: str, audit_root: Path = DEFAULT_AUDIT_ROOT) -> dict[str, Any]:
    path = _detail_path(run_id, audit_root)
    if not path.exists():
        raise FileNotFoundError(f"audit run not found: {run_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("audit detail must be object")
    return payload


def _resolve_composed_report_bundle(
    *,
    input_payload: dict[str, Any],
    run_id: str,
    include_model_augmentation: bool,
    audit_root: Path,
) -> dict[str, Any]:
    existing = input_payload.get("composed_report_bundle")
    if isinstance(existing, dict) and isinstance(existing.get("markdown"), str) and existing["markdown"].strip():
        return existing
    return build_composed_report_bundle(
        run_id=run_id,
        include_model_augmentation=include_model_augmentation,
        audit_root=audit_root,
    )


def _write_detail(run_id: str, detail: dict[str, Any], audit_root: Path = DEFAULT_AUDIT_ROOT) -> None:
    _atomic_write_json(_detail_path(run_id, audit_root), detail)


def finalize_released_audit(
    *,
    run_id: str,
    release_root: Path = DEFAULT_RELEASE_ROOT,
    package_name: str | None = None,
    package_version: str = "v1",
    include_model_augmentation: bool = True,
    audit_root: Path = DEFAULT_AUDIT_ROOT,
) -> dict[str, Any]:
    run_id = _require_non_empty_str(run_id, "run_id")
    if not isinstance(package_version, str) or not package_version.strip():
        raise ValueError("package_version must be non-empty string")

    detail = _load_detail(run_id, audit_root)
    input_payload = detail.get("input_payload")
    if not isinstance(input_payload, dict):
        raise ValueError("audit detail.input_payload must be present for finalization")

    coverage = build_control_coverage_matrix(run_id=run_id, audit_root=audit_root)
    dossier = build_audit_dossier(run_id=run_id, audit_root=audit_root)
    pre_export_release_gate = build_release_gate(run_id=run_id, audit_root=audit_root)

    if pre_export_release_gate.get("release_ready") is not True:
        raise ValueError(
            "audit is not release ready; blocking reasons: "
            + ", ".join(pre_export_release_gate.get("reasons_blocking_release", []))
        )

    composed_report = _resolve_composed_report_bundle(
        input_payload=input_payload,
        run_id=run_id,
        include_model_augmentation=include_model_augmentation,
        audit_root=audit_root,
    )

    final_payload = {
        **input_payload,
        "control_coverage_matrix": coverage,
        "audit_dossier": dossier,
        "release_gate": pre_export_release_gate,
        "composed_report_bundle": composed_report,
    }

    export_out = export_audit_package(
        payload=final_payload,
        export_root=release_root,
        package_name=package_name or f"released_{run_id}",
        package_version=package_version,
    )

    if export_out["verification"]["all_ok"] is not True:
        raise ValueError("newly finalized package failed verification")

    post_export_release_gate = {
        **pre_export_release_gate,
        "finalized_package_verification": export_out["verification"],
        "finalized_package_manifest": export_out["manifest"],
        "release_ready": True,
        "release_status": "RELEASE_READY",
    }

    finalization = {
        "run_id": run_id,
        "release_ready": True,
        "release_status": "FINALIZED",
        "package_version": package_version,
        "released_package": export_out,
        "release_gate": post_export_release_gate,
        "control_summary": coverage.get("summary", {}),
        "dossier_summary": {
            "control_count": dossier.get("control_count"),
            "overall_posture": dossier.get("overall_posture"),
            "deployment_decision": dossier.get("deployment_decision"),
        },
        "composed_report_summary": {
            "model_augmentation_present": composed_report.get("model_augmentation_present"),
            "finding_count": composed_report.get("finding_count"),
            "remediation_count": composed_report.get("remediation_count"),
            "report_source": export_out["manifest"].get("report_source"),
        },
    }

    _atomic_write_json(_finalization_path(run_id, audit_root), finalization)

    detail["release_finalization"] = {
        "release_status": "FINALIZED",
        "package_dir": export_out["package_paths"]["package_dir"],
        "manifest_path": export_out["package_paths"]["manifest_path"],
        "verification_all_ok": export_out["verification"]["all_ok"],
        "report_source": export_out["manifest"].get("report_source"),
    }
    _write_detail(run_id, detail, audit_root)

    return finalization


def get_release_finalization(
    *,
    run_id: str,
    audit_root: Path = DEFAULT_AUDIT_ROOT,
) -> dict[str, Any]:
    path = _finalization_path(run_id, audit_root)
    if not path.exists():
        raise FileNotFoundError(f"release finalization not found for run: {run_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("release finalization must be object")
    return payload


def render_release_finalization_markdown(
    *,
    run_id: str,
    audit_root: Path = DEFAULT_AUDIT_ROOT,
) -> str:
    payload = get_release_finalization(run_id=run_id, audit_root=audit_root)

    lines: list[str] = []
    lines.append(f"# Tenet Release Finalization: {run_id}")
    lines.append("")
    lines.append("## Final Status")
    lines.append("")
    lines.append(f"- Release ready: {payload.get('release_ready')}")
    lines.append(f"- Release status: {payload.get('release_status')}")
    lines.append(f"- Package version: {payload.get('package_version')}")
    lines.append("")
    lines.append("## Release Gate")
    lines.append("")
    gate = payload.get("release_gate", {})
    lines.append(f"- Overall posture: {gate.get('overall_posture')}")
    lines.append(f"- Deployment decision: {gate.get('deployment_decision')}")
    lines.append(f"- Release status: {gate.get('release_status')}")
    lines.append("")
    lines.append("## Coverage Summary")
    lines.append("")
    control_summary = payload.get("control_summary", {})
    lines.append(f"- Control count: {control_summary.get('control_count')}")
    lines.append(f"- Supported controls: {control_summary.get('supported_controls')}")
    lines.append(f"- Partial controls: {control_summary.get('partial_controls')}")
    lines.append(f"- Blocked controls: {control_summary.get('blocked_controls')}")
    lines.append("")
    lines.append("## Released Package")
    lines.append("")
    released = payload.get("released_package", {})
    package_paths = released.get("package_paths", {})
    verification = released.get("verification", {})
    manifest = released.get("manifest", {})
    lines.append(f"- Package dir: {package_paths.get('package_dir')}")
    lines.append(f"- Manifest path: {package_paths.get('manifest_path')}")
    lines.append(f"- Verification all_ok: {verification.get('all_ok')}")
    lines.append(f"- Report source: {manifest.get('report_source')}")
    lines.append("")
    return "\n".join(lines).strip() + "\n"
