from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.evidence_pack_service import DEFAULT_PACK_ROOT, EvidencePackPaths, get_evidence_pack
from core.evidence_processing_service import _load_index as _load_evidence_index
from core.model_manager import ModelManager
from core.model_tasks import (
    classify_document,
    explain_gap,
    extract_key_facts,
    write_executive_narrative,
)


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


def _pack_model_root(pack_id: str, pack_root: Path = DEFAULT_PACK_ROOT) -> Path:
    return EvidencePackPaths.for_pack(pack_id, pack_root).root / "model_augmented"


def _audit_model_root(run_id: str, audit_root: Path = DEFAULT_AUDIT_ROOT) -> Path:
    return audit_root / run_id / "model_augmented"


def augment_evidence_item_with_models(
    *,
    pack_id: str,
    evidence_id: str,
    model_manager: ModelManager | None = None,
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    get_evidence_pack(pack_id, pack_root=pack_root)
    index = _load_evidence_index(pack_id, pack_root)
    items = index.get("items", [])
    row = None
    for item in items:
        if isinstance(item, dict) and item.get("evidence_id") == evidence_id:
            row = item
            break
    if row is None:
        raise FileNotFoundError(f"evidence item not found: {evidence_id}")

    extracted_text_path = row.get("extracted_text_path")
    if not isinstance(extracted_text_path, str) or not extracted_text_path.strip():
        raise ValueError("evidence item has no extracted_text_path; process evidence first")

    text = Path(extracted_text_path).read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("extracted text is empty")

    mm = model_manager or ModelManager()

    classification = classify_document(
        filename=_require_non_empty_str(row.get("filename"), "filename"),
        extracted_text=text,
        model_manager=mm,
    )

    category = str(classification.get("category", "unclassified")).strip() or "unclassified"
    facts = extract_key_facts(
        category=category,
        extracted_text=text,
        model_manager=mm,
    )

    payload = {
        "evidence_id": evidence_id,
        "filename": row.get("filename"),
        "title": row.get("title"),
        "non_authoritative": True,
        "classification": classification,
        "key_facts": facts,
    }

    out_path = _pack_model_root(pack_id, pack_root) / f"{evidence_id}.augmentation.json"
    _atomic_write_json(out_path, payload)
    return payload


def augment_pack_evidence_with_models(
    *,
    pack_id: str,
    model_manager: ModelManager | None = None,
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    get_evidence_pack(pack_id, pack_root=pack_root)
    index = _load_evidence_index(pack_id, pack_root)
    items = index.get("items", [])

    augmented = []
    failures = []

    for row in items:
        if not isinstance(row, dict):
            continue
        evidence_id = row.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            continue
        try:
            augmented.append(
                augment_evidence_item_with_models(
                    pack_id=pack_id,
                    evidence_id=evidence_id,
                    model_manager=model_manager,
                    pack_root=pack_root,
                )
            )
        except Exception as exc:
            failures.append(
                {
                    "evidence_id": evidence_id,
                    "filename": row.get("filename"),
                    "error": str(exc),
                }
            )

    return {
        "pack_id": pack_id,
        "augmented_count": len(augmented),
        "failure_count": len(failures),
        "failures": failures,
        "items": augmented,
    }


def _load_audit_detail(run_id: str, audit_root: Path = DEFAULT_AUDIT_ROOT) -> dict[str, Any]:
    path = audit_root / run_id / "detail.json"
    if not path.exists():
        raise FileNotFoundError(f"audit run not found: {run_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("audit detail must be object")
    return payload


def augment_audit_report_with_models(
    *,
    run_id: str,
    model_manager: ModelManager | None = None,
    audit_root: Path = DEFAULT_AUDIT_ROOT,
) -> dict[str, Any]:
    detail = _load_audit_detail(run_id, audit_root)
    deterministic = detail.get("deterministic_audit_result", {})
    if not isinstance(deterministic, dict):
        raise ValueError("deterministic_audit_result must be object")

    summary = deterministic.get("summary", {})
    findings = deterministic.get("findings", [])
    if not isinstance(summary, dict):
        raise ValueError("summary must be object")
    if not isinstance(findings, list):
        raise ValueError("findings must be list")

    mm = model_manager or ModelManager()

    gap_narratives = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        requirement_text = (
            f"Control {finding.get('control_id')} under regime {finding.get('regime_id')} "
            "must be supported by sufficient evidence and effective implementation."
        )
        explanation = explain_gap(
            finding=finding,
            requirement_text=requirement_text,
            model_manager=mm,
        )
        gap_narratives.append(
            {
                "finding_id": finding.get("finding_id"),
                "control_id": finding.get("control_id"),
                "regime_id": finding.get("regime_id"),
                "non_authoritative": True,
                "explanation": explanation,
            }
        )

    highlights = []
    for finding in findings[:10]:
        if isinstance(finding, dict):
            highlights.append(
                {
                    "finding_id": finding.get("finding_id"),
                    "title": finding.get("title"),
                    "severity": finding.get("severity"),
                    "verdict": finding.get("verdict"),
                }
            )

    executive = write_executive_narrative(
        summary=summary,
        highlights=highlights,
        model_manager=mm,
    )

    payload = {
        "run_id": run_id,
        "non_authoritative": True,
        "executive_narrative": executive,
        "gap_narratives": gap_narratives,
    }

    out_path = _audit_model_root(run_id, audit_root) / "report_augmentation.json"
    _atomic_write_json(out_path, payload)
    return payload


def get_audit_report_augmentation(
    *,
    run_id: str,
    audit_root: Path = DEFAULT_AUDIT_ROOT,
) -> dict[str, Any]:
    path = _audit_model_root(run_id, audit_root) / "report_augmentation.json"
    if not path.exists():
        raise FileNotFoundError(f"report augmentation not found for run: {run_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("report augmentation must be object")
    return payload
