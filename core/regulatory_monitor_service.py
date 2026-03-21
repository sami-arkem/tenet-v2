from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.dataset_registry_service import DEFAULT_DATASET_ROOT, load_dataset_registry
from core.real_dataset_run_service import DEFAULT_SOURCE_RUN_ROOT


DEFAULT_ALERT_ROOT = Path("fixtures") / "regulatory_alerts"
DEFAULT_MONITOR_STATE_ROOT = DEFAULT_ALERT_ROOT / "_state"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_monitor_run_id() -> str:
    return f"regmon_{uuid.uuid4().hex[:16]}"


def new_alert_id() -> str:
    return f"alert_{uuid.uuid4().hex[:16]}"


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


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


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _iter_status_files(run_root: Path) -> list[Path]:
    if not run_root.exists():
        return []
    return sorted(run_root.glob("*/fetch_metadata.json"))


def _latest_real_source_fetches(run_root: Path = DEFAULT_SOURCE_RUN_ROOT) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for path in _iter_status_files(run_root):
        try:
            payload = _load_json(path)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        source_id = payload.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            continue
        existing = latest.get(source_id)
        if existing is None or str(payload.get("fetched_at") or "") > str(existing.get("fetched_at") or ""):
            latest[source_id] = payload
    return latest


def _monitor_state_path(root: Path = DEFAULT_MONITOR_STATE_ROOT) -> Path:
    return root / "dataset_change_state.json"


def load_monitor_state(root: Path = DEFAULT_MONITOR_STATE_ROOT) -> dict[str, Any]:
    path = _monitor_state_path(root)
    if not path.exists():
        return {
            "datasets": {},
            "updated_at": None,
        }
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("monitor state must be object")
    if not isinstance(payload.get("datasets"), dict):
        payload["datasets"] = {}
    return payload


def save_monitor_state(payload: dict[str, Any], root: Path = DEFAULT_MONITOR_STATE_ROOT) -> None:
    payload = _require_dict(payload, "monitor_state")
    payload["updated_at"] = utc_now_iso()
    _atomic_write_json(_monitor_state_path(root), payload)


def _alert_path(alert_id: str, root: Path = DEFAULT_ALERT_ROOT) -> Path:
    alert_id = _require_non_empty_str(alert_id, "alert_id")
    return root / f"{alert_id}.json"


def _monitor_run_path(run_id: str, root: Path = DEFAULT_ALERT_ROOT) -> Path:
    run_id = _require_non_empty_str(run_id, "run_id")
    return root / f"{run_id}.run.json"


def _dataset_change_fingerprint(dataset: dict[str, Any], fetch_meta: dict[str, Any] | None) -> dict[str, Any]:
    source_id = None
    metadata = dataset.get("metadata", {})
    if isinstance(metadata, dict):
        source_id = metadata.get("promoted_from_source_id")

    upstream_sha = None
    fetched_at = None
    if isinstance(fetch_meta, dict):
        upstream_sha = fetch_meta.get("raw_sha256")
        fetched_at = fetch_meta.get("fetched_at")

    if upstream_sha:
        fingerprint = upstream_sha
    else:
        stable = {
            "dataset_id": dataset.get("dataset_id"),
            "freshness_date": dataset.get("freshness_date"),
            "status": dataset.get("status"),
            "source_id": source_id,
            "last_ingested_at": dataset.get("last_ingested_at"),
        }
        fingerprint = _sha256_text(json.dumps(stable, sort_keys=True))

    return {
        "fingerprint": fingerprint,
        "source_id": source_id,
        "fetched_at": fetched_at,
    }


def _derive_affected_regimes(dataset: dict[str, Any]) -> list[str]:
    domain = str(dataset.get("domain") or "").strip().lower()
    mapping = {
        "aml": ["AML"],
        "kyc": ["KYC"],
        "kyb": ["KYB"],
        "sanctions": ["SANCTIONS"],
        "transaction_screening": ["SANCTIONS", "TM"],
        "vendor_risk": ["GOVERNANCE"],
        "governance": ["GOVERNANCE"],
        "fraud": ["TM"],
        "licensing": ["GOVERNANCE"],
    }
    return mapping.get(domain, [domain.upper()]) if domain else []


def _derive_controls_to_review(dataset: dict[str, Any]) -> list[str]:
    framework_ids = dataset.get("framework_ids", [])
    if not isinstance(framework_ids, list):
        framework_ids = []

    controls: list[str] = []
    for framework_id in framework_ids:
        if not isinstance(framework_id, str) or not framework_id.strip():
            continue
        value = framework_id.strip().upper()
        if value in {"UK_MLR", "EU_AMLD4", "EU_AMLD6", "FATF"}:
            controls.extend(["AML-01", "AML-04", "KYC-01"])
        elif value in {"OFAC", "OFSI"}:
            controls.extend(["SAN-02", "SAN-03", "SAN-04"])
        elif value in {"FCA_HANDBOOK"}:
            controls.extend(["GOV-01", "AML-16"])
        else:
            controls.append(f"{value}_REVIEW")

    deduped: list[str] = []
    seen: set[str] = set()
    for control in controls:
        if control not in seen:
            seen.add(control)
            deduped.append(control)
    return deduped


def _derive_urgency(dataset: dict[str, Any]) -> str:
    dataset_type = str(dataset.get("dataset_type") or "").strip().lower()
    if dataset_type in {"law_text", "sanctions_list_metadata"}:
        return "HIGH"
    if dataset_type in {"regulatory_guidance", "licensing_requirement"}:
        return "MEDIUM"
    return "LOW"


def _derive_change_type(dataset: dict[str, Any]) -> str:
    dataset_type = str(dataset.get("dataset_type") or "").strip().lower()
    if dataset_type == "sanctions_list_metadata":
        return "LIST_UPDATE"
    if dataset_type in {"law_text", "regulatory_guidance", "licensing_requirement"}:
        return "REGULATORY_UPDATE"
    return "REFERENCE_UPDATE"


def _build_alert(dataset: dict[str, Any], fetch_meta: dict[str, Any] | None) -> dict[str, Any]:
    dataset_id = _require_non_empty_str(dataset.get("dataset_id"), "dataset.dataset_id")
    title = _require_non_empty_str(dataset.get("title"), "dataset.title")
    metadata = dataset.get("metadata", {})
    source_id = metadata.get("promoted_from_source_id") if isinstance(metadata, dict) else None

    return {
        "alert_id": new_alert_id(),
        "dataset_id": dataset_id,
        "source_id": source_id,
        "title": f"Dataset changed: {title}",
        "summary": f"Detected a new upstream version or freshness state for {title}. Review impacted controls.",
        "jurisdictions": dataset.get("jurisdictions", []),
        "countries": dataset.get("countries", []),
        "framework_ids": dataset.get("framework_ids", []),
        "affected_regimes": _derive_affected_regimes(dataset),
        "change_type": _derive_change_type(dataset),
        "urgency": _derive_urgency(dataset),
        "affects_controls": True,
        "controls_to_review": _derive_controls_to_review(dataset),
        "published_at": (fetch_meta or {}).get("fetched_at"),
        "detected_at": utc_now_iso(),
        "deterministic_authoritative": True,
    }


def run_regulatory_monitor(
    *,
    dataset_root: Path = DEFAULT_DATASET_ROOT,
    run_root: Path = DEFAULT_SOURCE_RUN_ROOT,
    alert_root: Path = DEFAULT_ALERT_ROOT,
    state_root: Path = DEFAULT_MONITOR_STATE_ROOT,
) -> dict[str, Any]:
    registry = load_dataset_registry(dataset_root)
    latest_fetches = _latest_real_source_fetches(run_root)
    state = load_monitor_state(state_root)

    datasets_state = state.get("datasets", {})
    if not isinstance(datasets_state, dict):
        datasets_state = {}

    created_alerts: list[dict[str, Any]] = []
    unchanged_count = 0

    for dataset in registry["items"]:
        if not isinstance(dataset, dict):
            continue
        if dataset.get("status") != "ACTIVE":
            continue

        metadata = dataset.get("metadata", {})
        source_id = metadata.get("promoted_from_source_id") if isinstance(metadata, dict) else None
        fetch_meta = latest_fetches.get(source_id) if isinstance(source_id, str) else None
        fingerprint_payload = _dataset_change_fingerprint(dataset, fetch_meta)

        dataset_id = dataset["dataset_id"]
        new_fingerprint = fingerprint_payload["fingerprint"]
        old_fingerprint = datasets_state.get(dataset_id)

        if old_fingerprint is None:
            datasets_state[dataset_id] = new_fingerprint
            continue
        if old_fingerprint == new_fingerprint:
            unchanged_count += 1
            continue

        alert = _build_alert(dataset, fetch_meta)
        _atomic_write_json(_alert_path(alert["alert_id"], alert_root), alert)
        created_alerts.append(alert)
        datasets_state[dataset_id] = new_fingerprint

    state["datasets"] = datasets_state
    save_monitor_state(state, state_root)

    run_id = new_monitor_run_id()
    run_payload = {
        "run_id": run_id,
        "deterministic_authoritative": True,
        "started_at": utc_now_iso(),
        "dataset_count": registry["count"],
        "created_alert_count": len(created_alerts),
        "unchanged_count": unchanged_count,
        "alerts": created_alerts,
    }
    _atomic_write_json(_monitor_run_path(run_id, alert_root), run_payload)
    return run_payload


def list_regulatory_alerts(alert_root: Path = DEFAULT_ALERT_ROOT) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(alert_root.glob("alert_*.json")):
        try:
            payload = _load_json(path)
        except Exception:
            continue
        if isinstance(payload, dict):
            rows.append(payload)

    rows.sort(key=lambda row: str(row.get("detected_at") or ""), reverse=True)
    return {
        "count": len(rows),
        "items": rows,
        "deterministic_authoritative": True,
    }


def get_regulatory_alert(alert_id: str, alert_root: Path = DEFAULT_ALERT_ROOT) -> dict[str, Any]:
    path = _alert_path(alert_id, alert_root)
    if not path.exists():
        raise FileNotFoundError(f"regulatory alert not found: {alert_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("regulatory alert must be object")
    return payload


def list_monitor_runs(alert_root: Path = DEFAULT_ALERT_ROOT) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(alert_root.glob("regmon_*.run.json")):
        try:
            payload = _load_json(path)
        except Exception:
            continue
        if isinstance(payload, dict):
            rows.append(payload)

    rows.sort(key=lambda row: str(row.get("started_at") or ""), reverse=True)
    return {
        "count": len(rows),
        "items": rows,
        "deterministic_authoritative": True,
    }


def get_monitor_run(run_id: str, alert_root: Path = DEFAULT_ALERT_ROOT) -> dict[str, Any]:
    path = _monitor_run_path(run_id, alert_root)
    if not path.exists():
        raise FileNotFoundError(f"regulatory monitor run not found: {run_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("regulatory monitor run must be object")
    return payload
