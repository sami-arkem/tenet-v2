from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.model_augmentation_service import get_audit_report_augmentation


DEFAULT_AUDIT_ROOT = Path("artifacts") / "audit_runs"


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_audit_detail(run_id: str, audit_root: Path = DEFAULT_AUDIT_ROOT) -> dict[str, Any]:
    path = audit_root / run_id / "detail.json"
    if not path.exists():
        raise FileNotFoundError(f"audit run not found: {run_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("audit detail must be object")
    return payload


def _index_gap_narratives(augmentation: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(augmentation, dict):
        return {}
    rows = augmentation.get("gap_narratives", [])
    if not isinstance(rows, list):
        return {}

    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        finding_id = row.get("finding_id")
        if isinstance(finding_id, str) and finding_id.strip():
            out[finding_id] = row
    return out


def build_composed_report_payload(
    *,
    run_id: str,
    include_model_augmentation: bool = True,
    audit_root: Path = DEFAULT_AUDIT_ROOT,
) -> dict[str, Any]:
    detail = _load_audit_detail(run_id, audit_root)
    deterministic = _require_dict(detail.get("deterministic_audit_result"), "deterministic_audit_result")
    report_bundle = _require_dict(detail.get("report_bundle"), "report_bundle")
    report_pack = _require_dict(detail.get("report_pack"), "report_pack")

    augmentation = None
    if include_model_augmentation:
        try:
            augmentation = get_audit_report_augmentation(run_id=run_id, audit_root=audit_root)
        except FileNotFoundError:
            augmentation = None

    gap_narratives_by_id = _index_gap_narratives(augmentation)

    findings = []
    for finding in deterministic.get("findings", []):
        if not isinstance(finding, dict):
            continue
        finding_id = finding.get("finding_id")
        model_gap = gap_narratives_by_id.get(finding_id) if isinstance(finding_id, str) else None

        findings.append(
            {
                "finding_id": finding.get("finding_id"),
                "control_id": finding.get("control_id"),
                "regime_id": finding.get("regime_id"),
                "title": finding.get("title"),
                "severity": finding.get("severity"),
                "status": finding.get("status"),
                "verdict": finding.get("verdict"),
                "description": finding.get("description"),
                "rationale": finding.get("rationale"),
                "missing_evidence_types": finding.get("missing_evidence_types", []),
                "remediation_actions": finding.get("remediation_actions", []),
                "deterministic_authoritative": True,
                "model_gap_explanation": model_gap["explanation"] if isinstance(model_gap, dict) else None,
            }
        )

    payload = {
        "run_id": run_id,
        "deterministic_authoritative": True,
        "summary": deterministic.get("summary", {}),
        "company_profile": deterministic.get("company_profile", {}),
        "scope": deterministic.get("scope", {}),
        "findings": findings,
        "remediation_items": deterministic.get("remediation_items", []),
        "report_bundle": report_bundle,
        "report_pack": report_pack,
        "model_augmentation": {
            "present": augmentation is not None,
            "non_authoritative": True if augmentation else None,
            "executive_narrative": augmentation.get("executive_narrative") if isinstance(augmentation, dict) else None,
            "gap_narrative_count": len(augmentation.get("gap_narratives", [])) if isinstance(augmentation, dict) else 0,
        },
    }
    return payload


def render_composed_markdown_report(
    *,
    run_id: str,
    include_model_augmentation: bool = True,
    audit_root: Path = DEFAULT_AUDIT_ROOT,
) -> str:
    payload = build_composed_report_payload(
        run_id=run_id,
        include_model_augmentation=include_model_augmentation,
        audit_root=audit_root,
    )

    summary = payload["summary"]
    company = payload["company_profile"]
    scope = payload["scope"]
    findings = payload["findings"]
    remediation_items = payload["remediation_items"]
    model_aug = payload["model_augmentation"]

    lines: list[str] = []
    lines.append(f"# Tenet Composed Audit Report: {run_id}")
    lines.append("")
    lines.append("## Deterministic Executive Summary")
    lines.append("")
    lines.append(f"- Company: {company.get('company_name')}")
    lines.append(f"- Audit type: {scope.get('audit_type')}")
    lines.append(f"- Domains: {', '.join(scope.get('domains', []))}")
    lines.append(f"- Jurisdictions: {', '.join(scope.get('jurisdictions', []))}")
    lines.append(f"- Overall posture: {summary.get('overall_posture')}")
    lines.append(f"- Deployment decision: {summary.get('deployment_decision')}")
    lines.append(f"- Deterministic summary: {summary.get('summary_text')}")
    lines.append("")

    lines.append("## Authority Boundary")
    lines.append("")
    lines.append("- Deterministic findings, posture, and verdicts are authoritative.")
    lines.append("- Any model-generated text below is non-authoritative narrative only.")
    lines.append("- Model output never changes verdicts, findings, or deployment decisions.")
    lines.append("")

    if model_aug.get("present"):
        lines.append("## Model-Augmented Executive Narrative (Non-Authoritative)")
        lines.append("")
        narrative = model_aug.get("executive_narrative") or {}
        lines.append("> NON-AUTHORITATIVE MODEL NARRATIVE")
        lines.append(">")
        lines.append(f"> {narrative.get('narrative', 'No narrative available.')}")
        lines.append("")

    lines.append("## Deterministic Findings")
    lines.append("")
    if not findings:
        lines.append("- No findings.")
        lines.append("")
    else:
        for finding in findings:
            lines.append(f"### {finding.get('finding_id')}")
            lines.append(f"- Control: {finding.get('control_id')}")
            lines.append(f"- Regime: {finding.get('regime_id')}")
            lines.append(f"- Verdict: {finding.get('verdict')}")
            lines.append(f"- Severity: {finding.get('severity')}")
            lines.append(f"- Status: {finding.get('status')}")
            lines.append(f"- Title: {finding.get('title')}")
            lines.append(f"- Deterministic rationale: {finding.get('rationale')}")
            if finding.get("missing_evidence_types"):
                lines.append(f"- Missing evidence types: {', '.join(finding['missing_evidence_types'])}")
            if finding.get("remediation_actions"):
                lines.append("- Remediation actions:")
                for action in finding["remediation_actions"]:
                    lines.append(f"  - {action}")

            model_gap = finding.get("model_gap_explanation")
            if isinstance(model_gap, dict):
                lines.append("- Non-authoritative gap narrative:")
                lines.append(f"  - {model_gap.get('narrative')}")
            lines.append("")

    lines.append("## Deterministic Remediation Plan")
    lines.append("")
    if not remediation_items:
        lines.append("- No remediation items.")
        lines.append("")
    else:
        for item in remediation_items:
            if not isinstance(item, dict):
                continue
            lines.append(f"### {item.get('remediation_id')}")
            lines.append(f"- Finding: {item.get('finding_id')}")
            lines.append(f"- Owner: {item.get('owner')}")
            lines.append(f"- Status: {item.get('status')}")
            lines.append(f"- Action required: {item.get('action_required')}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_composed_report_bundle(
    *,
    run_id: str,
    include_model_augmentation: bool = True,
    audit_root: Path = DEFAULT_AUDIT_ROOT,
) -> dict[str, Any]:
    payload = build_composed_report_payload(
        run_id=run_id,
        include_model_augmentation=include_model_augmentation,
        audit_root=audit_root,
    )
    markdown = render_composed_markdown_report(
        run_id=run_id,
        include_model_augmentation=include_model_augmentation,
        audit_root=audit_root,
    )

    summary = payload["summary"]
    return {
        "run_id": run_id,
        "markdown": markdown,
        "deterministic_authoritative": True,
        "model_augmentation_present": payload["model_augmentation"]["present"],
        "overall_posture": summary.get("overall_posture"),
        "deployment_decision": summary.get("deployment_decision"),
        "finding_count": len(payload["findings"]),
        "remediation_count": len(payload["remediation_items"]),
    }
