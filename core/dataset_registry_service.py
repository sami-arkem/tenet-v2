from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


DEFAULT_DATASET_ROOT = Path("fixtures") / "regulatory_datasets"


ALLOWED_DATASET_TYPES = {
    "law_text",
    "regulatory_guidance",
    "enforcement_action",
    "sanctions_list_metadata",
    "aml_typology",
    "kyc_requirement",
    "vendor_risk_standard",
    "licensing_requirement",
    "fraud_pattern_reference",
    "transaction_monitoring_rule_reference",
}

ALLOWED_DATASET_STATUSES = {
    "ACTIVE",
    "DEPRECATED",
    "DRAFT",
}

ALLOWED_LICENSES = {
    "PUBLIC",
    "INTERNAL_USE_ONLY",
    "COMMERCIAL",
    "RESTRICTED",
}

ALLOWED_UPDATE_CADENCE = {
    "DAILY",
    "WEEKLY",
    "MONTHLY",
    "QUARTERLY",
    "AD_HOC",
    "STATIC",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


def _require_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
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


def _remove_tree(root: Path) -> None:
    if not root.exists():
        return
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    root.rmdir()


def _iter_json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*.json")
        if path.is_file() and "_ingested" not in path.parts and "_freshness" not in path.parts
    )


@dataclass(frozen=True)
class DatasetRecord:
    dataset_id: str
    title: str
    domain: str
    jurisdictions: list[str]
    countries: list[str]
    framework_ids: list[str]
    dataset_type: str
    license_type: str
    status: str
    update_cadence: str
    source_url: str | None
    loader_kind: str
    content_path: str | None
    freshness_date: str | None
    retrieval_ready: bool
    last_ingested_at: str | None
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "title": self.title,
            "domain": self.domain,
            "jurisdictions": self.jurisdictions,
            "countries": self.countries,
            "framework_ids": self.framework_ids,
            "dataset_type": self.dataset_type,
            "license_type": self.license_type,
            "status": self.status,
            "update_cadence": self.update_cadence,
            "source_url": self.source_url,
            "loader_kind": self.loader_kind,
            "content_path": self.content_path,
            "freshness_date": self.freshness_date,
            "retrieval_ready": self.retrieval_ready,
            "last_ingested_at": self.last_ingested_at,
            "metadata": self.metadata,
        }


def validate_dataset_manifest(payload: dict[str, Any], manifest_path: Path) -> DatasetRecord:
    payload = _require_dict(payload, "dataset_manifest")

    dataset_id = _require_non_empty_str(payload.get("dataset_id"), "dataset_manifest.dataset_id")
    title = _require_non_empty_str(payload.get("title"), "dataset_manifest.title")
    domain = _require_non_empty_str(payload.get("domain"), "dataset_manifest.domain")
    dataset_type = _require_non_empty_str(payload.get("dataset_type"), "dataset_manifest.dataset_type")
    if dataset_type not in ALLOWED_DATASET_TYPES:
        raise ValueError(f"dataset_type must be one of {sorted(ALLOWED_DATASET_TYPES)}")

    license_type = _require_non_empty_str(payload.get("license_type"), "dataset_manifest.license_type")
    if license_type not in ALLOWED_LICENSES:
        raise ValueError(f"license_type must be one of {sorted(ALLOWED_LICENSES)}")

    status = _require_non_empty_str(payload.get("status"), "dataset_manifest.status")
    if status not in ALLOWED_DATASET_STATUSES:
        raise ValueError(f"status must be one of {sorted(ALLOWED_DATASET_STATUSES)}")

    update_cadence = _require_non_empty_str(payload.get("update_cadence"), "dataset_manifest.update_cadence")
    if update_cadence not in ALLOWED_UPDATE_CADENCE:
        raise ValueError(f"update_cadence must be one of {sorted(ALLOWED_UPDATE_CADENCE)}")

    jurisdictions = [
        str(value).strip()
        for value in _require_list(payload.get("jurisdictions"), "dataset_manifest.jurisdictions")
        if str(value).strip()
    ]
    countries = [
        str(value).strip()
        for value in _require_list(payload.get("countries"), "dataset_manifest.countries")
        if str(value).strip()
    ]
    framework_ids = [
        str(value).strip()
        for value in _require_list(payload.get("framework_ids"), "dataset_manifest.framework_ids")
        if str(value).strip()
    ]
    if not jurisdictions:
        raise ValueError("dataset_manifest.jurisdictions must be non-empty")
    if not countries:
        raise ValueError("dataset_manifest.countries must be non-empty")
    if not framework_ids:
        raise ValueError("dataset_manifest.framework_ids must be non-empty")

    loader = _require_dict(payload.get("loader"), "dataset_manifest.loader")
    loader_kind = _require_non_empty_str(loader.get("kind"), "dataset_manifest.loader.kind")

    source_url = loader.get("source_url")
    if source_url is not None and (not isinstance(source_url, str) or not source_url.strip()):
        raise ValueError("dataset_manifest.loader.source_url must be non-empty string when present")

    content_path = loader.get("content_path")
    resolved_content_path: str | None = None
    if content_path is not None:
        content_path = _require_non_empty_str(content_path, "dataset_manifest.loader.content_path")
        resolved_content_path = str((manifest_path.parent / content_path).resolve())

    freshness = payload.get("freshness", {})
    if freshness is None:
        freshness = {}
    freshness = _require_dict(freshness, "dataset_manifest.freshness")
    freshness_date = freshness.get("as_of_date")
    if freshness_date is not None and (not isinstance(freshness_date, str) or not freshness_date.strip()):
        raise ValueError("dataset_manifest.freshness.as_of_date must be non-empty string when present")

    retrieval = payload.get("retrieval", {})
    if retrieval is None:
        retrieval = {}
    retrieval = _require_dict(retrieval, "dataset_manifest.retrieval")
    retrieval_ready = retrieval.get("ready")
    if not isinstance(retrieval_ready, bool):
        raise ValueError("dataset_manifest.retrieval.ready must be bool")
    last_ingested_at = retrieval.get("last_ingested_at")
    if last_ingested_at is not None and (not isinstance(last_ingested_at, str) or not last_ingested_at.strip()):
        raise ValueError("dataset_manifest.retrieval.last_ingested_at must be non-empty string when present")

    metadata = payload.get("metadata", {})
    if metadata is None:
        metadata = {}
    metadata = _require_dict(metadata, "dataset_manifest.metadata")

    return DatasetRecord(
        dataset_id=dataset_id,
        title=title,
        domain=domain,
        jurisdictions=jurisdictions,
        countries=countries,
        framework_ids=framework_ids,
        dataset_type=dataset_type,
        license_type=license_type,
        status=status,
        update_cadence=update_cadence,
        source_url=source_url.strip() if isinstance(source_url, str) else None,
        loader_kind=loader_kind,
        content_path=resolved_content_path,
        freshness_date=freshness_date.strip() if isinstance(freshness_date, str) else None,
        retrieval_ready=retrieval_ready,
        last_ingested_at=last_ingested_at.strip() if isinstance(last_ingested_at, str) else None,
        metadata=metadata,
    )


def load_dataset_registry(root: Path = DEFAULT_DATASET_ROOT) -> dict[str, Any]:
    files = _iter_json_files(root)
    records: list[DatasetRecord] = []
    errors: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for path in files:
        try:
            payload = _load_json(path)
            record = validate_dataset_manifest(payload, path)
            if record.dataset_id in seen_ids:
                raise ValueError(f"duplicate dataset_id: {record.dataset_id}")
            seen_ids.add(record.dataset_id)
            records.append(record)
        except Exception as exc:
            errors.append({"path": str(path), "error": str(exc)})

    records.sort(key=lambda item: item.dataset_id)
    return {
        "root": str(root),
        "count": len(records),
        "items": [item.to_dict() for item in records],
        "errors": errors,
    }


def _counter_from_items(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for item in items:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            counter[value.strip()] += 1
    return dict(sorted(counter.items()))


def _counter_from_nested_list(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for item in items:
        values = item.get(key, [])
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str) and value.strip():
                counter[value.strip()] += 1
    return dict(sorted(counter.items()))


def build_dataset_coverage_summary(root: Path = DEFAULT_DATASET_ROOT) -> dict[str, Any]:
    registry = load_dataset_registry(root)
    items = registry["items"]

    retrieval_ready_count = sum(1 for item in items if item.get("retrieval_ready") is True)
    active_count = sum(1 for item in items if item.get("status") == "ACTIVE")

    return {
        "deterministic_authoritative": True,
        "registry_count": registry["count"],
        "retrieval_ready_count": retrieval_ready_count,
        "active_count": active_count,
        "coverage": {
            "by_domain": _counter_from_items(items, "domain"),
            "by_dataset_type": _counter_from_items(items, "dataset_type"),
            "by_license_type": _counter_from_items(items, "license_type"),
            "by_jurisdiction": _counter_from_nested_list(items, "jurisdictions"),
            "by_country": _counter_from_nested_list(items, "countries"),
            "by_framework": _counter_from_nested_list(items, "framework_ids"),
        },
        "validation": {
            "errors": registry["errors"],
            "all_valid": len(registry["errors"]) == 0,
        },
        "generated_at": utc_now_iso(),
    }


def filter_datasets(
    *,
    domain: str | None = None,
    jurisdiction: str | None = None,
    country: str | None = None,
    framework_id: str | None = None,
    dataset_type: str | None = None,
    retrieval_ready_only: bool = False,
    root: Path = DEFAULT_DATASET_ROOT,
) -> dict[str, Any]:
    registry = load_dataset_registry(root)
    items = registry["items"]

    def match(item: dict[str, Any]) -> bool:
        if domain and item.get("domain") != domain:
            return False
        if jurisdiction and jurisdiction not in item.get("jurisdictions", []):
            return False
        if country and country not in item.get("countries", []):
            return False
        if framework_id and framework_id not in item.get("framework_ids", []):
            return False
        if dataset_type and item.get("dataset_type") != dataset_type:
            return False
        if retrieval_ready_only and item.get("retrieval_ready") is not True:
            return False
        return True

    filtered = [item for item in items if match(item)]
    return {
        "count": len(filtered),
        "items": filtered,
    }


def seed_example_datasets(root: Path = DEFAULT_DATASET_ROOT) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)

    # Reset generated artifacts so seeded example state is deterministic across reruns.
    _remove_tree(root / "_ingested")
    _remove_tree(root / "_freshness")
    _remove_tree(root / "promoted")

    examples = {
        "uk_aml_mlr.json": {
            "dataset_id": "dataset_uk_mlr_primary",
            "title": "UK Money Laundering Regulations Primary Text",
            "domain": "aml",
            "jurisdictions": ["uk"],
            "countries": ["GB"],
            "framework_ids": ["UK_MLR"],
            "dataset_type": "law_text",
            "license_type": "PUBLIC",
            "status": "ACTIVE",
            "update_cadence": "AD_HOC",
            "loader": {
                "kind": "url_manifest",
                "source_url": "https://example.org/uk-mlr",
            },
            "freshness": {
                "as_of_date": "2026-03-18",
            },
            "retrieval": {
                "ready": False,
            },
            "metadata": {
                "seeded": True,
                "priority": "high",
            },
        },
        "eu_aml_guidance.json": {
            "dataset_id": "dataset_eu_amld_guidance",
            "title": "EU AML Guidance Corpus",
            "domain": "aml",
            "jurisdictions": ["eu"],
            "countries": ["EU"],
            "framework_ids": ["EU_AMLD6"],
            "dataset_type": "regulatory_guidance",
            "license_type": "PUBLIC",
            "status": "ACTIVE",
            "update_cadence": "MONTHLY",
            "loader": {
                "kind": "url_manifest",
                "source_url": "https://example.org/eu-amld-guidance",
            },
            "freshness": {
                "as_of_date": "2026-03-18",
            },
            "retrieval": {
                "ready": False,
            },
            "metadata": {
                "seeded": True,
                "priority": "high",
            },
        },
        "ofac_sanctions_metadata.json": {
            "dataset_id": "dataset_us_ofac_metadata",
            "title": "OFAC Sanctions Metadata",
            "domain": "sanctions",
            "jurisdictions": ["us"],
            "countries": ["US"],
            "framework_ids": ["OFAC"],
            "dataset_type": "sanctions_list_metadata",
            "license_type": "PUBLIC",
            "status": "ACTIVE",
            "update_cadence": "DAILY",
            "loader": {
                "kind": "url_manifest",
                "source_url": "https://example.org/ofac-metadata",
            },
            "freshness": {
                "as_of_date": "2026-03-18",
            },
            "retrieval": {
                "ready": False,
            },
            "metadata": {
                "seeded": True,
                "priority": "critical",
            },
        },
        "global_vendor_risk.json": {
            "dataset_id": "dataset_global_vendor_risk_standard",
            "title": "Global Vendor Risk Standard Corpus",
            "domain": "vendor_risk",
            "jurisdictions": ["global"],
            "countries": ["GLOBAL"],
            "framework_ids": ["TPRM"],
            "dataset_type": "vendor_risk_standard",
            "license_type": "INTERNAL_USE_ONLY",
            "status": "ACTIVE",
            "update_cadence": "QUARTERLY",
            "loader": {
                "kind": "file_manifest",
                "content_path": "global_vendor_risk_corpus.md",
            },
            "freshness": {
                "as_of_date": "2026-03-18",
            },
            "retrieval": {
                "ready": False,
            },
            "metadata": {
                "seeded": True,
                "priority": "medium",
            },
        },
    }

    corpus_file = root / "global_vendor_risk_corpus.md"
    _atomic_write_text(
        corpus_file,
        "# Global Vendor Risk Standard Corpus\n\nCritical vendor due diligence baseline.\n",
    )

    created: list[str] = []
    for filename, payload in examples.items():
        path = root / filename
        _atomic_write_json(path, payload)
        created.append(str(path))

    return {"created": created}
