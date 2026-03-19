from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

DEFAULT_GOLD_CASE_ROOT = Path("fixtures") / "gold_cases"
DEFAULT_CUSTOMER_PACK_ROOT = Path("fixtures") / "customer_evidence_packs"


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


def _iter_json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.json") if path.is_file())


def _iter_gold_case_manifests(root: Path) -> list[Path]:
    return sorted(path for path in _iter_json_files(root) if "gold_case" in path.stem)


def _iter_customer_pack_manifests(root: Path) -> list[Path]:
    return sorted(path for path in _iter_json_files(root) if "customer_pack" in path.stem)


@dataclass(frozen=True)
class GoldCaseRecord:
    case_id: str
    title: str
    domain: str
    jurisdictions: list[str]
    framework_ids: list[str]
    expected_deployment_decision: str
    expected_overall_posture: str
    payload_path: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "domain": self.domain,
            "jurisdictions": self.jurisdictions,
            "framework_ids": self.framework_ids,
            "expected_deployment_decision": self.expected_deployment_decision,
            "expected_overall_posture": self.expected_overall_posture,
            "payload_path": self.payload_path,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class CustomerPackRecord:
    pack_id: str
    customer_name: str
    domain: str
    jurisdictions: list[str]
    framework_ids: list[str]
    manifest_path: str
    expected_executable: bool
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "customer_name": self.customer_name,
            "domain": self.domain,
            "jurisdictions": self.jurisdictions,
            "framework_ids": self.framework_ids,
            "manifest_path": self.manifest_path,
            "expected_executable": self.expected_executable,
            "metadata": self.metadata,
        }


def validate_gold_case_manifest(payload: dict[str, Any], manifest_path: Path) -> GoldCaseRecord:
    payload = _require_dict(payload, "gold_case_manifest")

    case_id = _require_non_empty_str(payload.get("case_id"), "gold_case_manifest.case_id")
    title = _require_non_empty_str(payload.get("title"), "gold_case_manifest.title")
    domain = _require_non_empty_str(payload.get("domain"), "gold_case_manifest.domain")

    jurisdictions = [
        str(value).strip()
        for value in _require_list(payload.get("jurisdictions"), "gold_case_manifest.jurisdictions")
        if str(value).strip()
    ]
    framework_ids = [
        str(value).strip()
        for value in _require_list(payload.get("framework_ids"), "gold_case_manifest.framework_ids")
        if str(value).strip()
    ]
    if not jurisdictions:
        raise ValueError("gold_case_manifest.jurisdictions must be non-empty")
    if not framework_ids:
        raise ValueError("gold_case_manifest.framework_ids must be non-empty")

    expected = _require_dict(payload.get("expected"), "gold_case_manifest.expected")
    expected_deployment_decision = _require_non_empty_str(
        expected.get("deployment_decision"),
        "gold_case_manifest.expected.deployment_decision",
    )
    expected_overall_posture = _require_non_empty_str(
        expected.get("overall_posture"),
        "gold_case_manifest.expected.overall_posture",
    )

    payload_path = _require_non_empty_str(payload.get("payload_path"), "gold_case_manifest.payload_path")
    metadata = payload.get("metadata", {})
    if metadata is None:
        metadata = {}
    metadata = _require_dict(metadata, "gold_case_manifest.metadata")

    return GoldCaseRecord(
        case_id=case_id,
        title=title,
        domain=domain,
        jurisdictions=jurisdictions,
        framework_ids=framework_ids,
        expected_deployment_decision=expected_deployment_decision,
        expected_overall_posture=expected_overall_posture,
        payload_path=str((manifest_path.parent / payload_path).resolve()),
        metadata=metadata,
    )


def validate_customer_pack_manifest(payload: dict[str, Any], manifest_path: Path) -> CustomerPackRecord:
    payload = _require_dict(payload, "customer_pack_manifest")

    pack_id = _require_non_empty_str(payload.get("pack_id"), "customer_pack_manifest.pack_id")
    customer_name = _require_non_empty_str(payload.get("customer_name"), "customer_pack_manifest.customer_name")
    domain = _require_non_empty_str(payload.get("domain"), "customer_pack_manifest.domain")

    jurisdictions = [
        str(value).strip()
        for value in _require_list(payload.get("jurisdictions"), "customer_pack_manifest.jurisdictions")
        if str(value).strip()
    ]
    framework_ids = [
        str(value).strip()
        for value in _require_list(payload.get("framework_ids"), "customer_pack_manifest.framework_ids")
        if str(value).strip()
    ]
    if not jurisdictions:
        raise ValueError("customer_pack_manifest.jurisdictions must be non-empty")
    if not framework_ids:
        raise ValueError("customer_pack_manifest.framework_ids must be non-empty")

    expected_executable = payload.get("expected_executable")
    if not isinstance(expected_executable, bool):
        raise ValueError("customer_pack_manifest.expected_executable must be bool")

    metadata = payload.get("metadata", {})
    if metadata is None:
        metadata = {}
    metadata = _require_dict(metadata, "customer_pack_manifest.metadata")

    return CustomerPackRecord(
        pack_id=pack_id,
        customer_name=customer_name,
        domain=domain,
        jurisdictions=jurisdictions,
        framework_ids=framework_ids,
        manifest_path=str(manifest_path.resolve()),
        expected_executable=expected_executable,
        metadata=metadata,
    )


def load_gold_case_registry(root: Path = DEFAULT_GOLD_CASE_ROOT) -> dict[str, Any]:
    files = _iter_gold_case_manifests(root)
    records: list[GoldCaseRecord] = []
    errors: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for path in files:
        try:
            payload = _load_json(path)
            record = validate_gold_case_manifest(payload, path)
            if record.case_id in seen_ids:
                raise ValueError(f"duplicate gold case_id: {record.case_id}")
            seen_ids.add(record.case_id)
            records.append(record)
        except Exception as exc:
            errors.append({"path": str(path), "error": str(exc)})

    records.sort(key=lambda item: item.case_id)
    return {
        "root": str(root),
        "count": len(records),
        "items": [item.to_dict() for item in records],
        "errors": errors,
    }


def load_customer_pack_registry(root: Path = DEFAULT_CUSTOMER_PACK_ROOT) -> dict[str, Any]:
    files = _iter_customer_pack_manifests(root)
    records: list[CustomerPackRecord] = []
    errors: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for path in files:
        try:
            payload = _load_json(path)
            record = validate_customer_pack_manifest(payload, path)
            if record.pack_id in seen_ids:
                raise ValueError(f"duplicate customer pack_id: {record.pack_id}")
            seen_ids.add(record.pack_id)
            records.append(record)
        except Exception as exc:
            errors.append({"path": str(path), "error": str(exc)})

    records.sort(key=lambda item: item.pack_id)
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


def build_proof_density_summary(
    *,
    gold_root: Path = DEFAULT_GOLD_CASE_ROOT,
    customer_pack_root: Path = DEFAULT_CUSTOMER_PACK_ROOT,
    target_gold_cases: int = 100,
    target_customer_packs: int = 20,
) -> dict[str, Any]:
    if not isinstance(target_gold_cases, int) or target_gold_cases <= 0:
        raise ValueError("target_gold_cases must be positive int")
    if not isinstance(target_customer_packs, int) or target_customer_packs <= 0:
        raise ValueError("target_customer_packs must be positive int")

    gold = load_gold_case_registry(gold_root)
    packs = load_customer_pack_registry(customer_pack_root)

    gold_items = gold["items"]
    pack_items = packs["items"]
    gold_count = int(gold["count"])
    pack_count = int(packs["count"])

    return {
        "deterministic_authoritative": True,
        "targets": {
            "gold_cases": target_gold_cases,
            "customer_packs": target_customer_packs,
        },
        "current": {
            "gold_cases": gold_count,
            "customer_packs": pack_count,
        },
        "remaining": {
            "gold_cases": max(0, target_gold_cases - gold_count),
            "customer_packs": max(0, target_customer_packs - pack_count),
        },
        "progress_percent": {
            "gold_cases": round((gold_count / target_gold_cases) * 100, 2),
            "customer_packs": round((pack_count / target_customer_packs) * 100, 2),
        },
        "coverage": {
            "gold_cases_by_domain": _counter_from_items(gold_items, "domain"),
            "customer_packs_by_domain": _counter_from_items(pack_items, "domain"),
            "gold_cases_by_jurisdiction": _counter_from_nested_list(gold_items, "jurisdictions"),
            "customer_packs_by_jurisdiction": _counter_from_nested_list(pack_items, "jurisdictions"),
            "gold_cases_by_framework": _counter_from_nested_list(gold_items, "framework_ids"),
            "customer_packs_by_framework": _counter_from_nested_list(pack_items, "framework_ids"),
        },
        "validation": {
            "gold_registry_errors": gold["errors"],
            "customer_pack_registry_errors": packs["errors"],
            "all_registries_valid": len(gold["errors"]) == 0 and len(packs["errors"]) == 0,
        },
    }


def seed_example_gold_case(root: Path = DEFAULT_GOLD_CASE_ROOT) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    payload_path = root / "example_payload.json"
    manifest_path = root / "example_gold_case.json"

    if not payload_path.exists():
        _atomic_write_json(
            payload_path,
            {
                "run_id": "gold_example_001",
                "company_profile": {
                    "company_name": "Example Fintech",
                    "industry": "fintech",
                    "primary_jurisdiction": "uk",
                    "additional_jurisdictions": ["eu"],
                    "products": ["payments"],
                    "entities": ["Example Fintech Ltd"],
                },
                "scope": {
                    "audit_id": "audit_example_001",
                    "audit_type": "aml_readiness_review",
                    "framework_ids": ["UK_MLR"],
                    "domain": "aml",
                    "domains": ["aml"],
                    "jurisdictions": ["uk"],
                    "in_scope_entities": ["Example Fintech Ltd"],
                    "in_scope_products": ["payments"],
                    "evaluation_date": "2026-03-18",
                    "historical_context_is_non_authoritative": True,
                    "deterministic_current_audit_truth_only": True,
                },
                "controls": [],
                "default_remediation_owner": "compliance@example.com",
            },
        )

    if not manifest_path.exists():
        _atomic_write_json(
            manifest_path,
            {
                "case_id": "gold_case_example_001",
                "title": "Example AML Gold Case",
                "domain": "aml",
                "jurisdictions": ["uk"],
                "framework_ids": ["UK_MLR"],
                "expected": {
                    "deployment_decision": "APPROVED",
                    "overall_posture": "GREEN",
                },
                "payload_path": "example_payload.json",
                "metadata": {"seeded": True},
            },
        )

    return {
        "gold_case_manifest": str(manifest_path),
        "payload_path": str(payload_path),
    }


def seed_example_customer_pack(root: Path = DEFAULT_CUSTOMER_PACK_ROOT) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "example_customer_pack.json"

    if not manifest_path.exists():
        _atomic_write_json(
            manifest_path,
            {
                "pack_id": "customer_pack_example_001",
                "customer_name": "Example Fintech",
                "domain": "aml",
                "jurisdictions": ["uk"],
                "framework_ids": ["UK_MLR"],
                "expected_executable": True,
                "metadata": {"seeded": True},
            },
        )

    return {"customer_pack_manifest": str(manifest_path)}
