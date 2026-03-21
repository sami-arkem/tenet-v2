from __future__ import annotations

from typing import Any, Dict, List

from src.reporting.build_report_pack import build_report_pack


def _title_lines(findings: List[Dict[str, Any]], limit: int = 5) -> List[str]:
    lines: List[str] = []
    for finding in findings[:limit]:
        title = str(finding.get("title", "") or "").strip()
        control_id = str(finding.get("control_id", "") or "").strip()
        severity = str(finding.get("severity", "") or "").strip()
        if not title:
            continue
        line = f"- {title}"
        if control_id:
            line += f" ({control_id})"
        if severity:
            line += f" [{severity}]"
        lines.append(line)
    return lines


def _control_lines(items: List[Dict[str, Any]], limit: int = 5) -> List[str]:
    lines: List[str] = []
    for item in items[:limit]:
        control_id = str(item.get("control_id", "") or "").strip()
        title = str(item.get("title", "") or "").strip()
        if control_id and title:
            lines.append(f"- {control_id}: {title}")
        elif control_id:
            lines.append(f"- {control_id}")
        elif title:
            lines.append(f"- {title}")
    return lines


def _historical_lines(hist: Dict[str, Any]) -> List[str]:
    if not hist.get("has_history"):
        return ["- No prior historical context available."]

    lines: List[str] = []
    decision = hist.get("prior_decision_trajectory", {}) or {}
    remediation = hist.get("prior_remediation_trajectory", {}) or {}

    if decision:
        status = str(decision.get("status", "") or "").strip()
        latest = str(decision.get("latest_decision", "") or "").strip()
        if status or latest:
            lines.append(f"- Prior decision trajectory: {status or 'unknown'}; latest prior decision: {latest or 'unknown'}")

    if remediation:
        status = str(remediation.get("status", "") or "").strip()
        if status:
            lines.append(f"- Prior remediation trajectory: {status}")

    for label, key in [
        ("Prior recurring missing controls", "prior_recurring_missing_controls"),
        ("Prior recurring findings", "prior_recurring_findings"),
        ("Repeated governance weaknesses", "repeated_governance_weaknesses"),
        ("Repeated screening weaknesses", "repeated_screening_weaknesses"),
        ("Repeated licensing weaknesses", "repeated_licensing_weaknesses"),
        ("Repeated remediation weaknesses", "repeated_remediation_weaknesses"),
    ]:
        values = hist.get(key, []) or []
        if values:
            lines.append(f"- {label}: {', '.join(values[:8])}")

    return lines or ["- Prior historical context exists but contained no summarizable recurring items."]


def build_deterministic_report_markdown_bundle(audit_output: Dict[str, Any]) -> Dict[str, str]:
    report_pack = build_report_pack(audit_output)

    executive = audit_output.get("executive_summary", {}) or {}
    decision = str(audit_output.get("deployment_decision", {}).get("status", "") or "")
    entity_name = (
        str(audit_output.get("entity_profile", {}).get("legal_name", "") or "").strip()
        or str(audit_output.get("entity_profile", {}).get("entity_name", "") or "").strip()
        or str(executive.get("system_or_business_reviewed", "") or "").strip()
        or "Unknown Entity"
    )
    findings = audit_output.get("findings", []) or []
    missing_controls = audit_output.get("missing_controls", []) or []
    roadmap = audit_output.get("remediation_roadmap", {}) or {}

    top_issue_lines = [f"- {x}" for x in executive.get("top_issues", [])[:5] if x]
    finding_lines = _title_lines(findings, limit=5)
    missing_control_lines = _control_lines(missing_controls, limit=5)
    immediate_actions = roadmap.get("immediate_0_30_days", []) or []
    immediate_lines = [f"- {x}" for x in immediate_actions[:5] if x]

    board_hist = _historical_lines(report_pack["board_memo"].get("historical_context", {}) or {})
    regulator_hist = _historical_lines(report_pack["regulator_memo"].get("historical_context", {}) or {})
    client_hist = _historical_lines(report_pack["client_report"].get("historical_context", {}) or {})

    board = "\n".join([
        "# Board Memo",
        "",
        f"Entity: {entity_name}",
        f"Deployment Decision: {decision}",
        "",
        "## Executive Position",
        str(executive.get("decision_summary", "") or "").strip(),
        "",
        "## Top Issues",
        *(top_issue_lines or ["- None stated"]),
        "",
        "## Priority Findings",
        *(finding_lines or ["- None identified"]),
        "",
        "## Prior / Historical Context",
        *board_hist,
    ]).strip() + "\n"

    regulator = "\n".join([
        "# Regulator Memo",
        "",
        f"Entity: {entity_name}",
        f"Deployment Decision: {decision}",
        "",
        "## Key Findings",
        *(finding_lines or ["- None identified"]),
        "",
        "## Missing Controls",
        *(missing_control_lines or ["- None identified"]),
        "",
        "## Prior / Historical Context",
        *regulator_hist,
    ]).strip() + "\n"

    client = "\n".join([
        "# Client Report",
        "",
        f"Entity: {entity_name}",
        f"Deployment Decision: {decision}",
        "",
        "## Summary",
        str(executive.get("overall_readiness", "") or "").strip(),
        "",
        "## Findings",
        *(finding_lines or ["- None identified"]),
        "",
        "## Immediate Actions",
        *(immediate_lines or ["- None stated"]),
        "",
        "## Missing Controls",
        *(missing_control_lines or ["- None identified"]),
        "",
        "## Prior / Historical Context",
        *client_hist,
    ]).strip() + "\n"

    return {
        "board_memo_markdown": board,
        "regulator_memo_markdown": regulator,
        "client_report_markdown": client,
    }
