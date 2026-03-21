from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from apps.api.schemas.audit_preparation import AuditPreparationSummary, EvidenceChecklistItem
from core.audit_application_service import _load_registry, _find_audit, default_paths
from core.evidence_application_service import EvidenceApplicationPaths, _load_items
from core.evidence_classification_service import EvidenceClassificationPaths, _load_rows as _load_classification_rows


DEFAULT_REQUIREMENTS: dict[tuple[str, str], list[dict[str, str]]] = {
    ("aml_periodic", "FCA"): [
        {"required_category": "policy", "label": "AML Policy"},
        {"required_category": "governance", "label": "Governance / Oversight Evidence"},
        {"required_category": "risk_assessment", "label": "Risk Assessment"},
    ],
    ("aml_periodic", "UK"): [
        {"required_category": "policy", "label": "AML Policy"},
        {"required_category": "governance", "label": "Governance / Oversight Evidence"},
        {"required_category": "risk_assessment", "label": "Risk Assessment"},
    ],
}


class AuditPreparationPaths:
    def __init__(self, base: str = "state") -> None:
        self.base = base
        self.requirements_dir = f"{base}/audit_prep"
        self.audit_app = default_paths(base)
        self.evidence = EvidenceApplicationPaths(base)
        self.classifications = EvidenceClassificationPaths(base)

    def requirements_path(self, audit_id: str) -> Path:
        return Path(self.requirements_dir) / audit_id / "requirements.json"

    def summary_path(self, audit_id: str) -> Path:
        return Path(self.requirements_dir) / audit_id / "preparation_summary.json"


def _read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ensure_audit_requirements(
    *,
    paths: AuditPreparationPaths,
    tenant_id: str,
    audit_id: str,
) -> List[dict]:
    registry = _load_registry(paths.audit_app)
    audit = _find_audit(registry, audit_id)
    if str(audit["tenant_id"]) != tenant_id:
        raise PermissionError("Forbidden")

    req_path = paths.requirements_path(audit_id)
    payload = _read_json(req_path)
    if payload:
        return list(payload.get("requirements", []))

    key = (str(audit["audit_kind"]), str(audit["framework"]))
    requirements = DEFAULT_REQUIREMENTS.get(key) or DEFAULT_REQUIREMENTS.get((str(audit["audit_kind"]), str(audit["jurisdiction"]))) or [
        {"required_category": "policy", "label": "Policy Evidence"},
        {"required_category": "governance", "label": "Governance Evidence"},
    ]

    payload = {
        "audit_id": audit_id,
        "tenant_id": tenant_id,
        "audit_kind": audit["audit_kind"],
        "framework": audit["framework"],
        "requirements": requirements,
    }
    _write_json(req_path, payload)
    return requirements


def build_audit_preparation_summary(
    *,
    paths: AuditPreparationPaths,
    tenant_id: str,
    audit_id: str,
) -> AuditPreparationSummary:
    registry = _load_registry(paths.audit_app)
    audit = _find_audit(registry, audit_id)
    if str(audit["tenant_id"]) != tenant_id:
        raise PermissionError("Forbidden")

    requirements = ensure_audit_requirements(
        paths=paths,
        tenant_id=tenant_id,
        audit_id=audit_id,
    )
    evidence_rows = [
        row for row in _load_items(paths.evidence)
        if str(row["tenant_id"]) == tenant_id and str(row["audit_id"]) == audit_id
    ]
    classification_rows = [
        row for row in _load_classification_rows(paths.classifications)
        if str(row["tenant_id"]) == tenant_id and str(row["audit_id"]) == audit_id
    ]
    class_by_evidence = {str(row["evidence_id"]): row for row in classification_rows}

    checklist: List[EvidenceChecklistItem] = []
    blocking_reasons: List[str] = []

    for idx, requirement in enumerate(requirements, start=1):
        required_category = str(requirement["required_category"])
        linked = []
        predicted_categories = []
        final_categories = []
        statuses = []
        item_blocking: List[str] = []

        for evidence in evidence_rows:
            classification = class_by_evidence.get(str(evidence["evidence_id"]))
            predicted = classification.get("predicted_category") if classification else evidence.get("classification_predicted_category")
            final = classification.get("final_category") if classification else evidence.get("classification_final_category")

            if predicted == required_category or final == required_category or str(evidence.get("evidence_category")) == required_category:
                linked.append(str(evidence["evidence_id"]))
                if predicted:
                    predicted_categories.append(str(predicted))
                if final:
                    final_categories.append(str(final))
                statuses.append(str(evidence["status"]))
                if classification:
                    review_status = str(classification.get("review_queue_status", "NONE"))
                    if review_status == "OCR_REQUIRED":
                        item_blocking.append("OCR required before this requirement is usable")
                    elif review_status == "CLASSIFICATION_REVIEW_REQUIRED":
                        item_blocking.append("Classification confirmation required")

        if not linked:
            status = "MISSING"
            item_blocking.append("Required evidence is missing")
        elif any(s in {"UPLOADING"} for s in statuses):
            status = "UPLOADING"
            item_blocking.append("Evidence upload in progress")
        elif any(s in {"PROCESSING"} for s in statuses):
            status = "PROCESSING"
            item_blocking.append("Evidence processing in progress")
        elif any("OCR required before this requirement is usable" == msg for msg in item_blocking):
            status = "OCR_REQUIRED"
        elif any("Classification confirmation required" == msg for msg in item_blocking):
            status = "REVIEW_REQUIRED"
        elif any(s in {"FAILED", "CANCELLED"} for s in statuses):
            status = "FAILED"
            item_blocking.append("Evidence failed or was cancelled")
        elif all(s == "READY" for s in statuses):
            status = "READY"
        else:
            status = "FAILED"

        checklist.append(
            EvidenceChecklistItem(
                requirement_id=f"{audit_id}:requirement:{idx}",
                audit_id=audit_id,
                tenant_id=tenant_id,
                audit_kind=str(audit["audit_kind"]),
                framework=str(audit["framework"]),
                required_category=required_category,
                label=str(requirement["label"]),
                status=status,
                linked_evidence_ids=sorted(dict.fromkeys(linked)),
                blocking_reasons=item_blocking,
                predicted_categories=sorted(dict.fromkeys(predicted_categories)),
                final_categories=sorted(dict.fromkeys(final_categories)),
            )
        )
        blocking_reasons.extend(item_blocking)

    total_ready = sum(1 for item in checklist if item.status == "READY")
    total_blocked = sum(1 for item in checklist if item.status != "READY")
    preparation_status = "READY" if total_blocked == 0 else "BLOCKED"

    summary = AuditPreparationSummary(
        audit_id=audit_id,
        tenant_id=tenant_id,
        preparation_status=preparation_status,
        total_requirements=len(checklist),
        total_ready=total_ready,
        total_blocked=total_blocked,
        checklist=checklist,
        blocking_reasons=blocking_reasons,
    )
    _write_json(paths.summary_path(audit_id), summary.model_dump())
    return summary
