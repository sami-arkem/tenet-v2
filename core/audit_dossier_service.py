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


def _load_detail(run_id: str, audit_root: Path = DEFAULT_AUDIT_ROOT) -> dict[str, Any]:
    path = _detail_path(run_id, audit_root)
    if not path.exists():
        raise FileNotFoundError(f"audit run not found: {run_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("audit detail must be object")
    return payload


def _load_coverage(run_id: str, audit_root: Path = DEFAULT_AUDIT_ROOT) -> dict[str, Any]:
    path = _coverage_path(run_id, audit_root)
    if not path.exists():
        raise FileNotFoundError(f"control coverage matrix not found for run: {run_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("control coverage matrix must be object")
    return payload


def _index_findings_by_control(findings: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        control_id = str(finding.get("control_id", "")).strip()
        if not control_id:
            continue
        out.setdefault(control_id, []).append(finding)
    return out


def _index_remediation_by_finding(remediation_items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for row in remediation_items:
        if not isinstance(row, dict):
            continue
        finding_id = str(row.get("finding_id", "")).strip()
        if not finding_id:
            continue
        out.setdefault(finding_id, []).append(row)
    return out


def _build_evidence_citations(direct_evidence: list[dict[str, Any]], context_matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    for row in direct_evidence:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "citation_type": "direct_evidence",
                "evidence_id": row.get("evidence_id"),
                "title": row.get("title"),
                "source_type": row.get("source_type"),
                "file_path": row.get("file_path"),
                "citation": row.get("citation"),
            }
        )

    for row in context_matches:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "citation_type": "retrieved_context",
                "chunk_id": row.get("chunk_id"),
                "evidence_id": row.get("evidence_id"),
                "filename": row.get("filename"),
                "title": row.get("title"),
                "source_type": row.get("source_type"),
                "score": row.get("score"),
                "excerpt": row.get("excerpt"),
                "question": row.get("question"),
            }
        )

    return out


def build_audit_dossier(
    *,
    run_id: str,
    audit_root: Path = DEFAULT_AUDIT_ROOT,
) -> dict[str, Any]:
    detail = _load_detail(run_id, audit_root)
    coverage = _load_coverage(run_id, audit_root)

    deterministic = detail.get("deterministic_audit_result", {})
    if not isinstance(deterministic, dict):
        raise ValueError("deterministic_audit_result must be object")

    summary = deterministic.get("summary", {})
    scope = deterministic.get("scope", {})
    company = deterministic.get("company_profile", {})
    findings = deterministic.get("findings", [])
    remediation_items = deterministic.get("remediation_items", [])

    if not isinstance(findings, list):
        raise ValueError("findings must be list")
    if not isinstance(remediation_items, list):
        raise ValueError("remediation_items must be list")

    findings_by_control = _index_findings_by_control(findings)
    remediation_by_finding = _index_remediation_by_finding(remediation_items)

    dossier_controls = []
    for row in coverage.get("controls", []):
        if not isinstance(row, dict):
            continue

        control_id = str(row.get("control_id", "")).strip()
        linked_findings = findings_by_control.get(control_id, [])

        linked_finding_rows = []
        for finding in linked_findings:
            finding_id = str(finding.get("finding_id", "")).strip()
            linked_finding_rows.append(
                {
                    "finding_id": finding_id,
                    "title": finding.get("title"),
                    "severity": finding.get("severity"),
                    "status": finding.get("status"),
                    "verdict": finding.get("verdict"),
                    "description": finding.get("description"),
                    "rationale": finding.get("rationale"),
                    "linked_remediation_items": remediation_by_finding.get(finding_id, []),
                }
            )

        dossier_controls.append(
            {
                "control_id": row.get("control_id"),
                "regime_id": row.get("regime_id"),
                "title": row.get("title"),
                "coverage_status": row.get("coverage_status"),
                "required_evidence_types": row.get("required_evidence_types", []),
                "covered_evidence_types": row.get("covered_evidence_types", []),
                "missing_required_evidence_types": row.get("missing_required_evidence_types", []),
                "rationale": row.get("rationale"),
                "deterministic_authoritative": True,
                "evidence_citations": _build_evidence_citations(
                    row.get("direct_evidence", []),
                    row.get("context_matches", []),
                ),
                "linked_findings": linked_finding_rows,
            }
        )

    payload = {
        "run_id": run_id,
        "deterministic_authoritative": True,
        "company_name": company.get("company_name"),
        "audit_type": scope.get("audit_type"),
        "overall_posture": summary.get("overall_posture"),
        "deployment_decision": summary.get("deployment_decision"),
        "summary_text": summary.get("summary_text"),
        "control_count": coverage.get("summary", {}).get("control_count"),
        "supported_controls": coverage.get("summary", {}).get("supported_controls"),
        "partial_controls": coverage.get("summary", {}).get("partial_controls"),
        "blocked_controls": coverage.get("summary", {}).get("blocked_controls"),
        "controls": dossier_controls,
    }

    _atomic_write_json(_dossier_path(run_id, audit_root), payload)
    return payload


def get_audit_dossier(
    *,
    run_id: str,
    audit_root: Path = DEFAULT_AUDIT_ROOT,
) -> dict[str, Any]:
    path = _dossier_path(run_id, audit_root)
    if not path.exists():
        raise FileNotFoundError(f"audit dossier not found for run: {run_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("audit dossier must be object")
    return payload


def render_audit_dossier_markdown(
    *,
    run_id: str,
    audit_root: Path = DEFAULT_AUDIT_ROOT,
) -> str:
    dossier = get_audit_dossier(run_id=run_id, audit_root=audit_root)

    lines: list[str] = []
    lines.append(f"# Tenet Deterministic Audit Dossier: {run_id}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- Company: {dossier.get('company_name')}")
    lines.append(f"- Audit type: {dossier.get('audit_type')}")
    lines.append(f"- Overall posture: {dossier.get('overall_posture')}")
    lines.append(f"- Deployment decision: {dossier.get('deployment_decision')}")
    lines.append(f"- Summary: {dossier.get('summary_text')}")
    lines.append("")
    lines.append("## Dossier Authority")
    lines.append("")
    lines.append("- This dossier is deterministic and authoritative.")
    lines.append("- Each control below is bound to direct evidence, retrieved context, missing evidence, findings, and remediation.")
    lines.append("")

    for control in dossier.get("controls", []):
        if not isinstance(control, dict):
            continue

        lines.append(f"## {control.get('control_id')} — {control.get('title')}")
        lines.append("")
        lines.append(f"- Regime: {control.get('regime_id')}")
        lines.append(f"- Coverage status: {control.get('coverage_status')}")
        lines.append(f"- Required evidence types: {', '.join(control.get('required_evidence_types', []))}")
        lines.append(f"- Covered evidence types: {', '.join(control.get('covered_evidence_types', []))}")
        if control.get("missing_required_evidence_types"):
            lines.append(f"- Missing required evidence types: {', '.join(control.get('missing_required_evidence_types', []))}")
        lines.append(f"- Deterministic rationale: {control.get('rationale')}")
        lines.append("")

        lines.append("### Evidence Citations")
        lines.append("")
        citations = control.get("evidence_citations", [])
        if not citations:
            lines.append("- None")
        else:
            for row in citations:
                if not isinstance(row, dict):
                    continue
                if row.get("citation_type") == "direct_evidence":
                    lines.append(
                        f"- Direct evidence: {row.get('title')} | {row.get('source_type')} | "
                        f"{row.get('file_path')} | {row.get('citation')}"
                    )
                else:
                    lines.append(
                        f"- Retrieved context: {row.get('title')} | chunk={row.get('chunk_id')} | "
                        f"score={row.get('score')} | question={row.get('question')}"
                    )
        lines.append("")

        lines.append("### Linked Findings")
        lines.append("")
        linked_findings = control.get("linked_findings", [])
        if not linked_findings:
            lines.append("- None")
        else:
            for finding in linked_findings:
                if not isinstance(finding, dict):
                    continue
                lines.append(
                    f"- {finding.get('finding_id')} | {finding.get('title')} | "
                    f"severity={finding.get('severity')} | verdict={finding.get('verdict')}"
                )
                remediations = finding.get("linked_remediation_items", [])
                if isinstance(remediations, list) and remediations:
                    for rem in remediations:
                        if not isinstance(rem, dict):
                            continue
                        lines.append(
                            f"  - remediation: {rem.get('remediation_id')} | "
                            f"owner={rem.get('owner')} | status={rem.get('status')}"
                        )
        lines.append("")

    return "\n".join(lines).strip() + "\n"
