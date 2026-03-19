from __future__ import annotations

from typing import Any

from core.audit_runtime import DeploymentDecision, DeterministicAuditResult


def _section(title: str) -> str:
    return f"## {title}\n"


def render_markdown_report(result: DeterministicAuditResult) -> str:
    if not isinstance(result, DeterministicAuditResult):
        raise ValueError("result must be DeterministicAuditResult")

    lines: list[str] = []
    lines.append(f"# Tenet Deterministic Audit Report: {result.run_id}\n")
    lines.append(f"Generated: {result.completed_at}\n")

    lines.append(_section("Executive Summary"))
    lines.append(f"- Company: {result.company_profile.company_name}")
    lines.append(f"- Industry: {result.company_profile.industry}")
    lines.append(f"- Primary jurisdiction: {result.company_profile.primary_jurisdiction}")
    lines.append(f"- Audit type: {result.scope.audit_type}")
    lines.append(f"- Domains: {', '.join(result.scope.domains)}")
    lines.append(f"- Jurisdictions: {', '.join(result.scope.jurisdictions)}")
    lines.append(f"- Overall posture: {result.summary.overall_posture.value}")
    lines.append(f"- Deployment decision: {result.summary.deployment_decision.value}")
    lines.append(f"- Summary: {result.summary.summary_text}\n")

    lines.append(_section("Deterministic Guardrails"))
    lines.append("- Current audit truth is authoritative.")
    lines.append("- Historical context is included only as prior context and never overrides current truth.")
    lines.append("- Findings below are evidence-grounded and control-specific.\n")

    lines.append(_section("Control Evaluations"))
    for row in result.control_evaluations:
        lines.append(f"### {row.control_id} ({row.regime_id})")
        lines.append(f"- Verdict: {row.verdict.value}")
        lines.append(f"- Evidence coverage ratio: {row.evidence_coverage_ratio}")
        lines.append(f"- Rationale: {row.rationale}")
        if row.evidence_refs:
            lines.append("- Evidence refs:")
            for ref in row.evidence_refs:
                lines.append(f"  - {ref.title} — {ref.citation}")
        else:
            lines.append("- Evidence refs: none")
        lines.append("")

    lines.append(_section("Findings"))
    if not result.findings:
        lines.append("- No open findings.\n")
    else:
        for finding in result.findings:
            lines.append(f"### {finding.finding_id}")
            lines.append(f"- Control: {finding.control_id}")
            lines.append(f"- Regime: {finding.regime_id}")
            lines.append(f"- Severity: {finding.severity.value}")
            lines.append(f"- Status: {finding.status.value}")
            lines.append(f"- Verdict: {finding.verdict.value}")
            lines.append(f"- Description: {finding.description}")
            lines.append(f"- Rationale: {finding.rationale}")
            if finding.missing_evidence_types:
                lines.append(f"- Missing evidence types: {', '.join(finding.missing_evidence_types)}")
            if finding.evidence_refs:
                lines.append("- Evidence refs:")
                for ref in finding.evidence_refs:
                    lines.append(f"  - {ref.title} — {ref.citation}")
            if finding.remediation_actions:
                lines.append("- Remediation actions:")
                for action in finding.remediation_actions:
                    lines.append(f"  - {action}")
            lines.append("")

    lines.append(_section("Remediation Plan"))
    if not result.remediation_items:
        lines.append("- No remediation items.\n")
    else:
        for item in result.remediation_items:
            lines.append(f"### {item.remediation_id}")
            lines.append(f"- Finding: {item.finding_id}")
            lines.append(f"- Owner: {item.owner}")
            lines.append(f"- Status: {item.status.value}")
            lines.append(f"- Action required: {item.action_required}")
            if item.due_date:
                lines.append(f"- Due date: {item.due_date}")
            lines.append("")

    lines.append(_section("Prior / Historical Context"))
    if result.prior_historical_context:
        for key, value in result.prior_historical_context.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- None provided.")
    lines.append("")

    lines.append(_section("Readiness Statement"))
    decision = result.summary.deployment_decision
    if decision == DeploymentDecision.APPROVED:
        lines.append("The system is ready for deployment based on current deterministic audit truth.")
    elif decision == DeploymentDecision.CONDITIONALLY_APPROVED:
        lines.append("The system is not fully ready; remediation is required before clean approval.")
    else:
        lines.append("The system is not ready for deployment based on current deterministic audit truth.")
    lines.append("")

    return "\n".join(lines)


def render_report_bundle(result: DeterministicAuditResult) -> dict[str, Any]:
    return {
        "run_id": result.run_id,
        "markdown": render_markdown_report(result),
        "deployment_decision": result.summary.deployment_decision.value,
        "overall_posture": result.summary.overall_posture.value,
        "finding_count": len(result.findings),
        "remediation_count": len(result.remediation_items),
    }
