from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.dataset_registry_service import DEFAULT_DATASET_ROOT, validate_dataset_manifest
from core.source_acquisition_service import (
    DEFAULT_SOURCE_REGISTRY_ROOT,
    evaluate_source_for_ingestion,
    load_source_registry,
)

SOURCE_CLASS_TO_DATASET_TYPE = {
    "PUBLIC_OFFICIAL": "law_text",
    "LICENSED": "regulatory_guidance",
    "CUSTOMER_PROVIDED": "kyc_requirement",
    "CONTRACT_AUTHORIZED": "regulatory_guidance",
}

LICENSE_TO_DATASET_LICENSE = {
    "PUBLIC": "PUBLIC",
    "LICENSED": "COMMERCIAL",
    "CUSTOMER_AUTHORIZED": "INTERNAL_USE_ONLY",
    "CONTRACT_AUTHORIZED": "COMMERCIAL",
}

DOMAIN_DEFAULT_FRAMEWORK = {
    "aml": "UK_MLR",
    "kyc": "KYC_BASELINE",
    "kyb": "KYB_BASELINE",
    "sanctions": "OFAC",
    "governance": "INT_GOV",
    "vendor_risk": "TPRM",
    "third_party_risk": "TPRM",
    "fraud": "FRAUD_BASELINE",
    "transaction_screening": "SCREENING_BASELINE",
    "licensing": "LICENSING_BASELINE",
}


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


def _safe_slug(value: str) -> str:
    value = _require_non_empty_str(value, "value")
    chars: list[str] = []
    for ch in value.lower():
        chars.append(ch if ch.isalnum() else "_")
    slug = "".join(chars).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    if not slug:
        raise ValueError("safe slug became empty")
    return slug


def _find_source_record(source_id: str, root: Path = DEFAULT_SOURCE_REGISTRY_ROOT) -> dict[str, Any]:
    source_id = _require_non_empty_str(source_id, "source_id")
    registry = load_source_registry(root)
    for item in registry["items"]:
        if item.get("source_id") == source_id:
            return _require_dict(item, "source_record")
    raise FileNotFoundError(f"source not found: {source_id}")


def _promoted_manifest_path(source_id: str, dataset_root: Path = DEFAULT_DATASET_ROOT) -> Path:
    return dataset_root / "promoted" / f"{_safe_slug(source_id)}.json"


def _build_dataset_manifest_from_source(
    *,
    source: dict[str, Any],
    override_domain: str | None = None,
    override_framework_ids: list[str] | None = None,
) -> dict[str, Any]:
    source_id = _require_non_empty_str(source.get("source_id"), "source.source_id")
    title = _require_non_empty_str(source.get("title"), "source.title")
    domain = _require_non_empty_str(override_domain or source.get("domain"), "source.domain")
    source_class = _require_non_empty_str(source.get("source_class"), "source.source_class")
    license_status = _require_non_empty_str(source.get("license_status"), "source.license_status")
    acquisition_method = _require_non_empty_str(source.get("acquisition_method"), "source.acquisition_method")

    jurisdictions = [str(x).strip() for x in source.get("jurisdictions", []) if str(x).strip()]
    countries = [str(x).strip() for x in source.get("countries", []) if str(x).strip()]
    if not jurisdictions:
        raise ValueError("source.jurisdictions must be non-empty")
    if not countries:
        raise ValueError("source.countries must be non-empty")

    if override_framework_ids:
        framework_ids = [str(x).strip() for x in override_framework_ids if str(x).strip()]
    else:
        framework_ids = [DOMAIN_DEFAULT_FRAMEWORK.get(domain, f"{domain.upper()}_BASELINE")]
    if not framework_ids:
        raise ValueError("framework_ids must be non-empty")

    dataset_type = SOURCE_CLASS_TO_DATASET_TYPE.get(source_class)
    if not dataset_type:
        raise ValueError(f"no dataset_type mapping for source_class={source_class}")

    mapped_license = LICENSE_TO_DATASET_LICENSE.get(license_status)
    if not mapped_license:
        raise ValueError(f"no dataset license mapping for license_status={license_status}")

    source_url = source.get("source_url")
    metadata = dict(source.get("metadata", {}) or {})
    metadata["promoted_from_source_id"] = source_id
    metadata["promotion_acquisition_method"] = acquisition_method
    metadata["promotion_owner"] = source.get("owner")

    loader_kind = "url_manifest" if isinstance(source_url, str) and source_url.strip() else "file_manifest"
    loader: dict[str, Any] = {"kind": loader_kind}
    if loader_kind == "url_manifest":
        loader["source_url"] = source_url.strip()
    else:
        loader["content_path"] = f"{_safe_slug(source_id)}.md"

    return {
        "dataset_id": f"dataset_{_safe_slug(source_id)}",
        "title": title,
        "domain": domain,
        "jurisdictions": jurisdictions,
        "countries": countries,
        "framework_ids": framework_ids,
        "dataset_type": dataset_type,
        "license_type": mapped_license,
        "status": "ACTIVE",
        "update_cadence": "AD_HOC",
        "loader": loader,
        "freshness": {
            "as_of_date": metadata.get("freshness_date") or "2026-03-18",
        },
        "retrieval": {
            "ready": False,
        },
        "metadata": metadata,
    }


def promote_source_to_dataset_manifest(
    *,
    source_id: str,
    dataset_root: Path = DEFAULT_DATASET_ROOT,
    source_root: Path = DEFAULT_SOURCE_REGISTRY_ROOT,
    override_domain: str | None = None,
    override_framework_ids: list[str] | None = None,
    write_stub_content_for_file_manifest: bool = True,
) -> dict[str, Any]:
    decision = evaluate_source_for_ingestion(source_id=source_id, root=source_root)
    if decision["decision"] != "APPROVE":
        raise ValueError(
            "source is not promotable; reasons: "
            + ", ".join(decision.get("reasons", []))
        )

    source = _find_source_record(source_id, source_root)
    manifest = _build_dataset_manifest_from_source(
        source=source,
        override_domain=override_domain,
        override_framework_ids=override_framework_ids,
    )

    path = _promoted_manifest_path(source_id, dataset_root)
    _atomic_write_json(path, manifest)

    if manifest["loader"]["kind"] == "file_manifest" and write_stub_content_for_file_manifest:
        content_path = path.parent / manifest["loader"]["content_path"]
        if not content_path.exists():
            _atomic_write_text(
                content_path,
                (
                    "# Promoted Dataset Stub\n\n"
                    f"source_id: {source_id}\n"
                    f"title: {manifest['title']}\n"
                    f"domain: {manifest['domain']}\n"
                    "status: promoted_for_curated_ingestion\n"
                ),
            )

    validated = validate_dataset_manifest(manifest, path)
    return {
        "source_id": source_id,
        "decision": decision["decision"],
        "dataset_manifest_path": str(path),
        "dataset_manifest": validated.to_dict(),
        "deterministic_authoritative": True,
    }


def promote_all_allowed_sources(
    *,
    dataset_root: Path = DEFAULT_DATASET_ROOT,
    source_root: Path = DEFAULT_SOURCE_REGISTRY_ROOT,
) -> dict[str, Any]:
    registry = load_source_registry(source_root)

    promoted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for item in registry["items"]:
        if not isinstance(item, dict):
            continue
        source_id = item.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            continue

        try:
            evaluation = evaluate_source_for_ingestion(source_id=source_id, root=source_root)
            if evaluation["decision"] != "APPROVE":
                skipped.append(
                    {
                        "source_id": source_id,
                        "decision": evaluation["decision"],
                        "reasons": evaluation["reasons"],
                    }
                )
                continue

            promoted.append(
                promote_source_to_dataset_manifest(
                    source_id=source_id,
                    dataset_root=dataset_root,
                    source_root=source_root,
                )
            )
        except Exception as exc:
            failures.append({"source_id": source_id, "error": str(exc)})

    return {
        "promoted_count": len(promoted),
        "skipped_count": len(skipped),
        "failure_count": len(failures),
        "promoted": promoted,
        "skipped": skipped,
        "failures": failures,
        "deterministic_authoritative": True,
    }
