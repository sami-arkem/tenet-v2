from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

DEFAULT_AUDIT_ROOT = Path("artifacts") / "audit_runs"


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


def _detail_path(run_id: str, audit_root: Path = DEFAULT_AUDIT_ROOT) -> Path:
    return audit_root / _require_non_empty_str(run_id, "run_id") / "detail.json"


def _coverage_path(run_id: str, audit_root: Path = DEFAULT_AUDIT_ROOT) -> Path:
    return audit_root / _require_non_empty_str(run_id, "run_id") / "control_coverage.json"


def _dossier_path(run_id: str, audit_root: Path = DEFAULT_AUDIT_ROOT) -> Path:
    return audit_root / _require_non_empty_str(run_id, "run_id") / "audit_dossier.json"


def _review_path(run_id: str, audit_root: Path = DEFAULT_AUDIT_ROOT) -> Path:
    return audit_root / _require_non_empty_str(run_id, "run_id") / "review_state.json"


def _release_gate_path(run_id: str, audit_root: Path = DEFAULT_AUDIT_ROOT) -> Path:
    return audit_root / _require_non_empty_str(run_id, "run_id") / "release_gate.json"


def _load_required_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be object")
    return payload


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"optional json must be object: {path}")
    return payload


def _extract_export_verification(detail: dict[str, Any]) -> dict[str, Any]:
    export_package = detail.get("export_package")
    if not isinstance(export_package, dict):
        return {
            "present": False,
            "verified": False,
            "all_ok": False,
            "verification": None,
        }

    verification = export_package.get("verification")
    all_ok = bool(isinstance(verification, dict) and verification.get("all_ok") is True)
    return {
        "present": True,
        "verified": all_ok,
        "all_ok": all_ok,
        "verification": verification,
    }


def build_release_gate(
    *,
    run_id: str,
    audit_root: Path = DEFAULT_AUDIT_ROOT,
) -> dict[str, Any]:
    detail = _load_required_json(_detail_path(run_id, audit_root), "audit detail")
    coverage = _load_required_json(_coverage_path(run_id, audit_root), "control coverage")
    dossier = _load_required_json(_dossier_path(run_id, audit_root), "audit dossier")
    review = _load_optional_json(_review_path(run_id, audit_root))

    deterministic = detail.get("deterministic_audit_result", {})
    if not isinstance(deterministic, dict):
        raise ValueError("deterministic_audit_result must be object")

    summary = deterministic.get("summary", {})
    scope = deterministic.get("scope", {})
    company = deterministic.get("company_profile", {})

    if not isinstance(summary, dict):
        raise ValueError("summary must be object")
    if not isinstance(scope, dict):
        raise ValueError("scope must be object")
    if not isinstance(company, dict):
        raise ValueError("company_profile must be object")

    deployment_decision = str(summary.get("deployment_decision", "")).strip()
    overall_posture = str(summary.get("overall_posture", "")).strip()

    coverage_summary = coverage.get("summary", {})
    if not isinstance(coverage_summary, dict):
        raise ValueError("coverage.summary must be object")

    supported_controls = int(coverage_summary.get("supported_controls", 0) or 0)
    partial_controls = int(coverage_summary.get("partial_controls", 0) or 0)
    blocked_controls = int(coverage_summary.get("blocked_controls", 0) or 0)
    control_count = int(coverage_summary.get("control_count", 0) or 0)

    export_state = _extract_export_verification(detail)

    review_status = None
    latest_review_decision = None
    latest_review = None
    if isinstance(review, dict):
        review_status = review.get("status")
        latest_review = review.get("latest_review")
        if isinstance(latest_review, dict):
            latest_review_decision = latest_review.get("decision")

    reasons_blocking_release: list[str] = []

    if deployment_decision != "APPROVED":
        reasons_blocking_release.append(
            f"deterministic_deployment_decision_not_approved:{deployment_decision or 'UNKNOWN'}"
        )
    if overall_posture != "GREEN":
        reasons_blocking_release.append(
            f"overall_posture_not_green:{overall_posture or 'UNKNOWN'}"
        )
    if control_count <= 0:
        reasons_blocking_release.append("no_controls_in_coverage_matrix")
    if partial_controls > 0:
        reasons_blocking_release.append(f"partial_controls_present:{partial_controls}")
    if blocked_controls > 0:
        reasons_blocking_release.append(f"blocked_controls_present:{blocked_controls}")
    if not isinstance(dossier, dict) or dossier.get("deterministic_authoritative") is not True:
        reasons_blocking_release.append("audit_dossier_missing_or_not_authoritative")

    if review is None:
        reasons_blocking_release.append("review_state_missing")
    else:
        if review_status != "REVIEWED":
            reasons_blocking_release.append(f"review_not_completed:{review_status}")
        if latest_review_decision != "APPROVED":
            reasons_blocking_release.append(
                f"review_decision_not_approved:{latest_review_decision or 'UNKNOWN'}"
            )

    if export_state["present"] is not True:
        reasons_blocking_release.append("export_package_missing")
    elif export_state["all_ok"] is not True:
        reasons_blocking_release.append("export_package_verification_failed")

    release_ready = len(reasons_blocking_release) == 0
    release_status = "RELEASE_READY" if release_ready else "RELEASE_BLOCKED"

    payload = {
        "run_id": run_id,
        "deterministic_authoritative": True,
        "release_status": release_status,
        "release_ready": release_ready,
        "company_name": company.get("company_name"),
        "audit_type": scope.get("audit_type"),
        "overall_posture": overall_posture,
        "deployment_decision": deployment_decision,
        "control_summary": {
            "control_count": control_count,
            "supported_controls": supported_controls,
            "partial_controls": partial_controls,
            "blocked_controls": blocked_controls,
        },
        "review_summary": {
            "present": review is not None,
            "status": review_status,
            "latest_review_decision": latest_review_decision,
            "latest_review": latest_review,
        },
        "export_summary": export_state,
        "reasons_blocking_release": reasons_blocking_release,
    }

    _atomic_write_json(_release_gate_path(run_id, audit_root), payload)
    return payload


def get_release_gate(
    *,
    run_id: str,
    audit_root: Path = DEFAULT_AUDIT_ROOT,
) -> dict[str, Any]:
    return _load_required_json(_release_gate_path(run_id, audit_root), "release gate")


def render_release_gate_markdown(
    *,
    run_id: str,
    audit_root: Path = DEFAULT_AUDIT_ROOT,
) -> str:
    gate = get_release_gate(run_id=run_id, audit_root=audit_root)

    lines: list[str] = []
    lines.append(f"# Tenet Release Gate: {run_id}")
    lines.append("")
    lines.append("## Deterministic Release Decision")
    lines.append("")
    lines.append(f"- Company: {gate.get('company_name')}")
    lines.append(f"- Audit type: {gate.get('audit_type')}")
    lines.append(f"- Release status: {gate.get('release_status')}")
    lines.append(f"- Release ready: {gate.get('release_ready')}")
    lines.append(f"- Overall posture: {gate.get('overall_posture')}")
    lines.append(f"- Deployment decision: {gate.get('deployment_decision')}")
    lines.append("")
    lines.append("## Control Summary")
    lines.append("")
    control_summary = gate.get("control_summary", {})
    lines.append(f"- Control count: {control_summary.get('control_count')}")
    lines.append(f"- Supported controls: {control_summary.get('supported_controls')}")
    lines.append(f"- Partial controls: {control_summary.get('partial_controls')}")
    lines.append(f"- Blocked controls: {control_summary.get('blocked_controls')}")
    lines.append("")
    lines.append("## Review Summary")
    lines.append("")
    review_summary = gate.get("review_summary", {})
    lines.append(f"- Review present: {review_summary.get('present')}")
    lines.append(f"- Review status: {review_summary.get('status')}")
    lines.append(f"- Latest review decision: {review_summary.get('latest_review_decision')}")
    lines.append("")
    lines.append("## Export Verification")
    lines.append("")
    export_summary = gate.get("export_summary", {})
    lines.append(f"- Export present: {export_summary.get('present')}")
    lines.append(f"- Export verified: {export_summary.get('verified')}")
    lines.append("")
    lines.append("## Blocking Reasons")
    lines.append("")
    reasons = gate.get("reasons_blocking_release", [])
    if isinstance(reasons, list) and reasons:
        for reason in reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("- none")
    lines.append("")

    return "\n".join(lines)
