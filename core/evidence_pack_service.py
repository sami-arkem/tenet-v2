from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from api.store import DEFAULT_STORE_ROOT, execute_and_store_audit


DEFAULT_PACK_ROOT = Path("artifacts") / "evidence_packs"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_pack_id() -> str:
    return f"pack_{uuid.uuid4().hex[:16]}"


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return value


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


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


@dataclass(frozen=True)
class EvidencePackPaths:
    root: Path
    manifest_path: Path
    detail_path: Path

    @staticmethod
    def for_pack(pack_id: str, pack_root: Path = DEFAULT_PACK_ROOT) -> "EvidencePackPaths":
        pack_id = _require_non_empty_str(pack_id, "pack_id")
        root = pack_root / pack_id
        return EvidencePackPaths(
            root=root,
            manifest_path=root / "manifest.json",
            detail_path=root / "detail.json",
        )


def _validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = _require_dict(manifest, "manifest")

    company_profile = _require_dict(manifest.get("company_profile"), "manifest.company_profile")
    scope = _require_dict(manifest.get("scope"), "manifest.scope")
    controls = _require_list(manifest.get("controls"), "manifest.controls")
    evidence_catalog = _require_list(manifest.get("evidence_catalog"), "manifest.evidence_catalog")

    _require_non_empty_str(company_profile.get("company_name"), "manifest.company_profile.company_name")
    _require_non_empty_str(company_profile.get("industry"), "manifest.company_profile.industry")
    _require_non_empty_str(company_profile.get("primary_jurisdiction"), "manifest.company_profile.primary_jurisdiction")
    _require_list(company_profile.get("additional_jurisdictions"), "manifest.company_profile.additional_jurisdictions")
    _require_list(company_profile.get("products"), "manifest.company_profile.products")
    _require_list(company_profile.get("entities"), "manifest.company_profile.entities")

    _require_non_empty_str(scope.get("audit_id"), "manifest.scope.audit_id")
    _require_non_empty_str(scope.get("audit_type"), "manifest.scope.audit_type")
    _require_non_empty_str(scope.get("domain"), "manifest.scope.domain")
    _require_list(scope.get("domains"), "manifest.scope.domains")
    _require_list(scope.get("jurisdictions"), "manifest.scope.jurisdictions")
    _require_list(scope.get("framework_ids"), "manifest.scope.framework_ids")
    _require_list(scope.get("in_scope_entities"), "manifest.scope.in_scope_entities")
    _require_list(scope.get("in_scope_products"), "manifest.scope.in_scope_products")
    _require_non_empty_str(scope.get("evaluation_date"), "manifest.scope.evaluation_date")

    if scope.get("historical_context_is_non_authoritative") is not True:
        raise ValueError("manifest.scope.historical_context_is_non_authoritative must be true")
    if scope.get("deterministic_current_audit_truth_only") is not True:
        raise ValueError("manifest.scope.deterministic_current_audit_truth_only must be true")

    for idx, control_row in enumerate(controls):
        control_row = _require_dict(control_row, f"manifest.controls[{idx}]")
        control = _require_dict(control_row.get("control"), f"manifest.controls[{idx}].control")
        _require_non_empty_str(control.get("control_id"), f"manifest.controls[{idx}].control.control_id")
        _require_non_empty_str(control.get("regime_id"), f"manifest.controls[{idx}].control.regime_id")
        _require_non_empty_str(control.get("title"), f"manifest.controls[{idx}].control.title")
        _require_non_empty_str(control.get("description"), f"manifest.controls[{idx}].control.description")
        _require_non_empty_str(control.get("test_procedure"), f"manifest.controls[{idx}].control.test_procedure")
        _require_list(control.get("required_evidence_types"), f"manifest.controls[{idx}].control.required_evidence_types")
        _require_non_empty_str(control.get("severity_if_missing"), f"manifest.controls[{idx}].control.severity_if_missing")
        if not isinstance(control_row.get("declared_control_present"), bool):
            raise ValueError(f"manifest.controls[{idx}].declared_control_present must be bool")
        provided = _require_list(control_row.get("provided_evidence"), f"manifest.controls[{idx}].provided_evidence")
        for ev_idx, ev in enumerate(provided):
            ev = _require_dict(ev, f"manifest.controls[{idx}].provided_evidence[{ev_idx}]")
            _require_non_empty_str(ev.get("evidence_id"), f"manifest.controls[{idx}].provided_evidence[{ev_idx}].evidence_id")
            _require_non_empty_str(ev.get("title"), f"manifest.controls[{idx}].provided_evidence[{ev_idx}].title")
            _require_non_empty_str(ev.get("source_type"), f"manifest.controls[{idx}].provided_evidence[{ev_idx}].source_type")
            _require_non_empty_str(ev.get("file_path"), f"manifest.controls[{idx}].provided_evidence[{ev_idx}].file_path")
            _require_non_empty_str(ev.get("citation"), f"manifest.controls[{idx}].provided_evidence[{ev_idx}].citation")

    evidence_ids: set[str] = set()
    for idx, row in enumerate(evidence_catalog):
        row = _require_dict(row, f"manifest.evidence_catalog[{idx}]")
        evidence_id = _require_non_empty_str(row.get("evidence_id"), f"manifest.evidence_catalog[{idx}].evidence_id")
        if evidence_id in evidence_ids:
            raise ValueError(f"duplicate evidence_id in evidence_catalog: {evidence_id}")
        evidence_ids.add(evidence_id)
        _require_non_empty_str(row.get("title"), f"manifest.evidence_catalog[{idx}].title")
        _require_non_empty_str(row.get("source_type"), f"manifest.evidence_catalog[{idx}].source_type")
        _require_non_empty_str(row.get("file_path"), f"manifest.evidence_catalog[{idx}].file_path")
        _require_non_empty_str(row.get("citation"), f"manifest.evidence_catalog[{idx}].citation")

    return manifest


def create_evidence_pack(
    *,
    name: str,
    manifest: dict[str, Any],
    created_by: str,
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    name = _require_non_empty_str(name, "name")
    created_by = _require_non_empty_str(created_by, "created_by")
    manifest = _validate_manifest(manifest)

    pack_id = new_pack_id()
    paths = EvidencePackPaths.for_pack(pack_id, pack_root)

    now = utc_now_iso()
    detail = {
        "pack_id": pack_id,
        "name": name,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "status": "READY",
        "manifest_summary": {
            "company_name": manifest["company_profile"]["company_name"],
            "audit_type": manifest["scope"]["audit_type"],
            "domain": manifest["scope"]["domain"],
            "jurisdictions": manifest["scope"]["jurisdictions"],
            "control_count": len(manifest["controls"]),
            "evidence_count": len(manifest["evidence_catalog"]),
        },
        "latest_execution": None,
    }

    paths.root.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(paths.manifest_path, manifest)
    _atomic_write_json(paths.detail_path, detail)

    return detail


def list_evidence_packs(pack_root: Path = DEFAULT_PACK_ROOT) -> list[dict[str, Any]]:
    if not pack_root.exists():
        return []

    rows: list[dict[str, Any]] = []
    for pack_dir in sorted([path for path in pack_root.iterdir() if path.is_dir()]):
        detail_path = pack_dir / "detail.json"
        if not detail_path.exists():
            continue
        try:
            rows.append(_load_json(detail_path))
        except Exception:
            continue

    rows.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return rows


def get_evidence_pack(pack_id: str, pack_root: Path = DEFAULT_PACK_ROOT) -> dict[str, Any]:
    paths = EvidencePackPaths.for_pack(pack_id, pack_root)
    if not paths.detail_path.exists():
        raise FileNotFoundError(f"evidence pack not found: {pack_id}")
    detail = _load_json(paths.detail_path)
    manifest = _load_json(paths.manifest_path)
    return {
        "detail": detail,
        "manifest": manifest,
    }


def execute_evidence_pack(
    *,
    pack_id: str,
    run_id: str,
    default_remediation_owner: str,
    metadata: dict[str, Any] | None = None,
    export: dict[str, Any] | None = None,
    pack_root: Path = DEFAULT_PACK_ROOT,
    store_root: Path = DEFAULT_STORE_ROOT,
) -> dict[str, Any]:
    from core.audit_planner import build_execution_payload_from_pack
    from core.evidence_processing_service import build_corpus_readiness

    pack_id = _require_non_empty_str(pack_id, "pack_id")
    run_id = _require_non_empty_str(run_id, "run_id")
    default_remediation_owner = _require_non_empty_str(default_remediation_owner, "default_remediation_owner")

    loaded = get_evidence_pack(pack_id, pack_root)
    detail = loaded["detail"]
    manifest = loaded["manifest"]

    readiness = build_corpus_readiness(pack_id, pack_root=pack_root)
    if readiness["corpus_ready"] is not True:
        raise ValueError("evidence corpus is not ready for execution")

    if manifest.get("controls"):
        payload = {
            "run_id": run_id,
            "company_profile": manifest["company_profile"],
            "scope": manifest["scope"],
            "controls": manifest["controls"],
            "default_remediation_owner": default_remediation_owner,
            "prior_historical_context": manifest.get("prior_historical_context", {}),
            "metadata": {
                **manifest.get("metadata", {}),
                **(metadata or {}),
                "evidence_pack_id": pack_id,
                "evidence_pack_name": detail["name"],
                "corpus_ready": True,
                "ready_evidence_count": readiness["ready_count"],
            },
        }
    else:
        payload = build_execution_payload_from_pack(pack_id, pack_root=pack_root)
        payload["run_id"] = run_id
        payload["default_remediation_owner"] = default_remediation_owner
        payload["metadata"] = {
            **payload.get("metadata", {}),
            **(metadata or {}),
            "corpus_ready": True,
            "ready_evidence_count": readiness["ready_count"],
        }

    execution_detail = execute_and_store_audit(
        payload=payload,
        export=export,
        store_root=store_root,
    )

    detail["updated_at"] = utc_now_iso()
    detail["latest_execution"] = {
        "run_id": execution_detail["run_id"],
        "created_at": detail["updated_at"],
        "deployment_decision": execution_detail["topline"]["deployment_decision"],
        "overall_posture": execution_detail["topline"]["overall_posture"],
        "finding_count": execution_detail["topline"]["finding_count"],
    }

    paths = EvidencePackPaths.for_pack(pack_id, pack_root)
    _atomic_write_json(paths.detail_path, detail)

    return {
        "pack_id": pack_id,
        "pack_name": detail["name"],
        "execution": execution_detail,
    }
