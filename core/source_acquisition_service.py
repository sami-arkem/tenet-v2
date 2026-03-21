from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


DEFAULT_SOURCE_REGISTRY_ROOT = Path("fixtures") / "source_registry"

ALLOWED_SOURCE_CLASSES = {
    "PUBLIC_OFFICIAL",
    "LICENSED",
    "CUSTOMER_PROVIDED",
    "CONTRACT_AUTHORIZED",
    "SCRAPED_PROHIBITED",
}

ALLOWED_ACQUISITION_METHODS = {
    "PUBLIC_DOWNLOAD",
    "LICENSED_FEED",
    "CUSTOMER_UPLOAD",
    "CONTRACTUAL_TRANSFER",
    "SCRAPED_UNAUTHORIZED",
}

ALLOWED_LICENSE_STATUSES = {
    "PUBLIC",
    "LICENSED",
    "CUSTOMER_AUTHORIZED",
    "CONTRACT_AUTHORIZED",
    "RESTRICTED",
    "PROHIBITED",
}

ALLOWED_FRESHNESS_CHECKS = {
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "ad_hoc",
    "static",
}

INDEX_FILENAME = "_index.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be bool")
    return value


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


def _iter_json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*.json")
        if path.is_file() and path.name != INDEX_FILENAME
    )


def _index_path(root: Path = DEFAULT_SOURCE_REGISTRY_ROOT) -> Path:
    return root / INDEX_FILENAME


def _parse_iso8601(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized)


def _freshness_max_age_days(mode: str) -> int | None:
    mapping = {
        "daily": 1,
        "weekly": 7,
        "monthly": 31,
        "quarterly": 93,
        "ad_hoc": None,
        "static": None,
    }
    return mapping[mode]


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    title: str
    domain: str
    jurisdictions: list[str]
    countries: list[str]
    source_class: str
    acquisition_method: str
    license_status: str
    owner: str
    source_url: str | None
    approved: bool
    retrieval_allowed: bool
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "domain": self.domain,
            "jurisdictions": self.jurisdictions,
            "countries": self.countries,
            "source_class": self.source_class,
            "acquisition_method": self.acquisition_method,
            "license_status": self.license_status,
            "owner": self.owner,
            "source_url": self.source_url,
            "approved": self.approved,
            "retrieval_allowed": self.retrieval_allowed,
            "metadata": self.metadata,
        }


def validate_source_manifest(payload: dict[str, Any], manifest_path: Path) -> SourceRecord:
    payload = _require_dict(payload, "source_manifest")

    source_id = _require_non_empty_str(payload.get("source_id"), "source_manifest.source_id")
    title = _require_non_empty_str(payload.get("title"), "source_manifest.title")
    domain = _require_non_empty_str(payload.get("domain"), "source_manifest.domain")

    jurisdictions = [
        str(value).strip()
        for value in _require_list(payload.get("jurisdictions"), "source_manifest.jurisdictions")
        if str(value).strip()
    ]
    countries = [
        str(value).strip()
        for value in _require_list(payload.get("countries"), "source_manifest.countries")
        if str(value).strip()
    ]
    if not jurisdictions:
        raise ValueError("source_manifest.jurisdictions must be non-empty")
    if not countries:
        raise ValueError("source_manifest.countries must be non-empty")

    source_class = _require_non_empty_str(payload.get("source_class"), "source_manifest.source_class")
    if source_class not in ALLOWED_SOURCE_CLASSES:
        raise ValueError(f"source_class must be one of {sorted(ALLOWED_SOURCE_CLASSES)}")

    acquisition_method = _require_non_empty_str(
        payload.get("acquisition_method"),
        "source_manifest.acquisition_method",
    )
    if acquisition_method not in ALLOWED_ACQUISITION_METHODS:
        raise ValueError(f"acquisition_method must be one of {sorted(ALLOWED_ACQUISITION_METHODS)}")

    license_status = _require_non_empty_str(payload.get("license_status"), "source_manifest.license_status")
    if license_status not in ALLOWED_LICENSE_STATUSES:
        raise ValueError(f"license_status must be one of {sorted(ALLOWED_LICENSE_STATUSES)}")

    owner = _require_non_empty_str(payload.get("owner"), "source_manifest.owner")
    approved = _require_bool(payload.get("approved"), "source_manifest.approved")
    retrieval_allowed = _require_bool(payload.get("retrieval_allowed"), "source_manifest.retrieval_allowed")

    source_url = payload.get("source_url")
    if source_url is not None:
        source_url = _require_non_empty_str(source_url, "source_manifest.source_url")

    metadata = payload.get("metadata", {})
    if metadata is None:
        metadata = {}
    metadata = _require_dict(metadata, "source_manifest.metadata")

    freshness_check = metadata.get("freshness_check")
    if freshness_check is not None:
        freshness_check = _require_non_empty_str(freshness_check, "source_manifest.metadata.freshness_check").lower()
        if freshness_check not in ALLOWED_FRESHNESS_CHECKS:
            raise ValueError(f"freshness_check must be one of {sorted(ALLOWED_FRESHNESS_CHECKS)}")
        metadata["freshness_check"] = freshness_check

    last_check = metadata.get("last_check")
    if last_check is not None:
        parsed = _parse_iso8601(_require_non_empty_str(last_check, "source_manifest.metadata.last_check"))
        metadata["last_check"] = parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    metadata["manifest_path"] = str(manifest_path.resolve())
    return SourceRecord(
        source_id=source_id,
        title=title,
        domain=domain,
        jurisdictions=jurisdictions,
        countries=countries,
        source_class=source_class,
        acquisition_method=acquisition_method,
        license_status=license_status,
        owner=owner,
        source_url=source_url,
        approved=approved,
        retrieval_allowed=retrieval_allowed,
        metadata=metadata,
    )


def load_source_registry(root: Path = DEFAULT_SOURCE_REGISTRY_ROOT) -> dict[str, Any]:
    files = _iter_json_files(root)
    records: list[SourceRecord] = []
    errors: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for path in files:
        try:
            record = validate_source_manifest(_load_json(path), path)
            if record.source_id in seen_ids:
                raise ValueError(f"duplicate source_id: {record.source_id}")
            seen_ids.add(record.source_id)
            records.append(record)
        except Exception as exc:
            errors.append({"path": str(path), "error": str(exc)})

    records.sort(key=lambda item: item.source_id)
    return {
        "root": str(root),
        "count": len(records),
        "items": [item.to_dict() for item in records],
        "errors": errors,
    }


def rebuild_source_index(root: Path = DEFAULT_SOURCE_REGISTRY_ROOT) -> dict[str, dict[str, Any]]:
    registry = load_source_registry(root)
    index: dict[str, dict[str, Any]] = {}
    for item in registry["items"]:
        source_id = item["source_id"]
        item_with_checksum = dict(item)
        item_with_checksum["_checksum"] = hashlib.sha256(
            json.dumps(item_with_checksum, sort_keys=True).encode("utf-8")
        ).hexdigest()
        index[source_id] = item_with_checksum
    _atomic_write_json(
        _index_path(root),
        {
            "sources": index,
            "count": len(index),
            "built_at": utc_now_iso(),
        },
    )
    return index


def get_source_by_id(source_id: str, root: Path = DEFAULT_SOURCE_REGISTRY_ROOT) -> dict[str, Any] | None:
    source_id = _require_non_empty_str(source_id, "source_id")
    index_path = _index_path(root)
    if index_path.exists():
        payload = _load_json(index_path)
        sources = payload.get("sources", {})
        if isinstance(sources, dict):
            row = sources.get(source_id)
            if isinstance(row, dict):
                return row
    for item in load_source_registry(root)["items"]:
        if item["source_id"] == source_id:
            return item
    return None


def robots_allowed(source_url: str | None) -> bool:
    if not isinstance(source_url, str) or not source_url.strip():
        return False

    parsed = urlparse(source_url)
    if not parsed.scheme or not parsed.netloc:
        return False

    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
        return bool(parser.can_fetch("TenetSourceAcquisitionBot", source_url))
    except Exception:
        return False


def check_source_freshness(record: SourceRecord, max_age_days: int | None = None) -> bool:
    freshness_check = record.metadata.get("freshness_check")
    last_check = record.metadata.get("last_check")

    if freshness_check is None or last_check is None:
        return True

    freshness_check = _require_non_empty_str(freshness_check, "record.metadata.freshness_check").lower()
    if freshness_check not in ALLOWED_FRESHNESS_CHECKS:
        raise ValueError(f"freshness_check must be one of {sorted(ALLOWED_FRESHNESS_CHECKS)}")

    if max_age_days is None:
        max_age_days = _freshness_max_age_days(freshness_check)
    if max_age_days is None:
        return True

    checked_at = _parse_iso8601(_require_non_empty_str(last_check, "record.metadata.last_check"))
    now = datetime.now(timezone.utc)
    return now - checked_at.astimezone(timezone.utc) <= timedelta(days=max_age_days)


def _evaluate_source_row(source: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []

    source_class = source.get("source_class")
    license_status = source.get("license_status")
    approved = source.get("approved") is True
    retrieval_allowed = source.get("retrieval_allowed") is True

    if source_class == "SCRAPED_PROHIBITED":
        reasons.append("blocked_source_class:SCRAPED_PROHIBITED")
    if not approved:
        reasons.append("approval_missing_or_false")
    if not retrieval_allowed:
        reasons.append("retrieval_not_allowed")
    if license_status in {"PROHIBITED", "RESTRICTED"}:
        reasons.append(f"license_not_authorized:{license_status}")

    decision = "APPROVE" if not reasons else "BLOCK"
    return {
        "source_id": source["source_id"],
        "decision": decision,
        "reasons": reasons or ["approved_for_ingestion"],
        "source": source,
    }


def evaluate_source_for_ingestion(
    *,
    source_id: str,
    root: Path = DEFAULT_SOURCE_REGISTRY_ROOT,
) -> dict[str, Any]:
    source = get_source_by_id(source_id, root)
    if source is None:
        raise FileNotFoundError(f"source not found: {source_id}")
    return _evaluate_source_row(source)


def evaluate_source_for_ingestion_enhanced(
    *,
    source_id: str,
    root: Path = DEFAULT_SOURCE_REGISTRY_ROOT,
) -> dict[str, Any]:
    source = get_source_by_id(source_id, root)
    if source is None:
        raise FileNotFoundError(f"source not found: {source_id}")

    baseline = _evaluate_source_row(source)
    record = SourceRecord(
        source_id=source["source_id"],
        title=source["title"],
        domain=source["domain"],
        jurisdictions=list(source["jurisdictions"]),
        countries=list(source["countries"]),
        source_class=source["source_class"],
        acquisition_method=source["acquisition_method"],
        license_status=source["license_status"],
        owner=source["owner"],
        source_url=source.get("source_url"),
        approved=bool(source["approved"]),
        retrieval_allowed=bool(source["retrieval_allowed"]),
        metadata=dict(source.get("metadata", {})),
    )

    robots_ok = True if record.source_url is None else robots_allowed(record.source_url)
    freshness_ok = check_source_freshness(record)
    license_ok = record.license_status not in {"PROHIBITED", "RESTRICTED"}

    reasons = [reason for reason in baseline["reasons"] if reason != "approved_for_ingestion"]
    if record.source_url is not None and not robots_ok:
        reasons.append("robots_txt_blocked")
    if not freshness_ok:
        reasons.append("freshness_check_failed")
    if not license_ok:
        reasons.append(f"license_not_authorized:{record.license_status}")

    decision = "APPROVE" if not reasons else "BLOCK"
    return {
        "source_id": record.source_id,
        "decision": decision,
        "reasons": reasons or ["approved_for_ingestion"],
        "source": source,
        "provenance_checks": {
            "robots_ok": robots_ok,
            "freshness_ok": freshness_ok,
            "license_ok": license_ok,
            "approved": record.approved,
            "retrieval_allowed": record.retrieval_allowed,
        },
    }


def build_source_registry_summary(root: Path = DEFAULT_SOURCE_REGISTRY_ROOT) -> dict[str, Any]:
    registry = load_source_registry(root)
    items = registry["items"]

    def counter_from_items(key: str) -> dict[str, int]:
        counter: Counter[str] = Counter()
        for item in items:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                counter[value.strip()] += 1
        return dict(sorted(counter.items()))

    def counter_from_nested_list(key: str) -> dict[str, int]:
        counter: Counter[str] = Counter()
        for item in items:
            values = item.get(key, [])
            if not isinstance(values, list):
                continue
            for value in values:
                if isinstance(value, str) and value.strip():
                    counter[value.strip()] += 1
        return dict(sorted(counter.items()))

    approved_count = sum(1 for item in items if item.get("approved") is True)
    retrieval_allowed_count = sum(1 for item in items if item.get("retrieval_allowed") is True)

    return {
        "deterministic_authoritative": True,
        "registry_count": registry["count"],
        "approved_count": approved_count,
        "retrieval_allowed_count": retrieval_allowed_count,
        "coverage": {
            "by_domain": counter_from_items("domain"),
            "by_source_class": counter_from_items("source_class"),
            "by_license_status": counter_from_items("license_status"),
            "by_jurisdiction": counter_from_nested_list("jurisdictions"),
            "by_country": counter_from_nested_list("countries"),
        },
        "validation": {
            "errors": registry["errors"],
            "all_valid": len(registry["errors"]) == 0,
        },
    }


def seed_example_sources(root: Path = DEFAULT_SOURCE_REGISTRY_ROOT) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)

    recent_check = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    examples = {
        "regulatory_feeds/uk_fca_handbook_public.json": {
            "source_id": "uk_fca_handbook_public",
            "title": "UK FCA Handbook Public Source",
            "domain": "aml",
            "jurisdictions": ["uk"],
            "countries": ["GB"],
            "source_class": "PUBLIC_OFFICIAL",
            "acquisition_method": "PUBLIC_DOWNLOAD",
            "license_status": "PUBLIC",
            "owner": "tenet",
            "source_url": "https://www.fca.org.uk/handbook",
            "approved": True,
            "retrieval_allowed": True,
            "metadata": {
                "freshness_check": "daily",
                "last_check": recent_check,
            },
        },
        "compliance_docs/customer_uploaded_authorized.json": {
            "source_id": "customer_uploaded_authorized",
            "title": "Customer Provided Authorized Corpus",
            "domain": "vendor_risk",
            "jurisdictions": ["global"],
            "countries": ["GLOBAL"],
            "source_class": "CUSTOMER_PROVIDED",
            "acquisition_method": "CUSTOMER_UPLOAD",
            "license_status": "CUSTOMER_AUTHORIZED",
            "owner": "customer",
            "source_url": None,
            "approved": True,
            "retrieval_allowed": True,
            "metadata": {
                "freshness_check": "static",
                "last_check": recent_check,
            },
        },
        "regulatory_feeds/licensed_vendor_feed.json": {
            "source_id": "licensed_vendor_feed",
            "title": "Licensed Vendor Feed",
            "domain": "sanctions",
            "jurisdictions": ["us"],
            "countries": ["US"],
            "source_class": "LICENSED",
            "acquisition_method": "LICENSED_FEED",
            "license_status": "LICENSED",
            "owner": "tenet",
            "source_url": "https://licensed.example.com/feed",
            "approved": True,
            "retrieval_allowed": True,
            "metadata": {
                "freshness_check": "weekly",
                "last_check": recent_check,
            },
        },
        "blocked/blocked_scraped_prohibited.json": {
            "source_id": "blocked_scraped_prohibited",
            "title": "Blocked Scraped Prohibited Source",
            "domain": "aml",
            "jurisdictions": ["us"],
            "countries": ["US"],
            "source_class": "SCRAPED_PROHIBITED",
            "acquisition_method": "SCRAPED_UNAUTHORIZED",
            "license_status": "PROHIBITED",
            "owner": "unknown",
            "source_url": "https://blocked.example.com/data",
            "approved": False,
            "retrieval_allowed": False,
            "metadata": {
                "freshness_check": "daily",
                "last_check": recent_check,
            },
        },
    }

    created: list[str] = []
    for relative_path, payload in examples.items():
        path = root / relative_path
        _atomic_write_json(path, payload)
        created.append(str(path))

    rebuild_source_index(root)
    return {"created": created}
