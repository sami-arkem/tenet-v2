from __future__ import annotations

from typing import Any, Dict, List

from src.memory.historical_context import build_historical_context


def _safe_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def build_report_pack(audit_output: Dict[str, Any]) -> Dict[str, Any]:
    executive = audit_output.get("executive_summary", {}) or {}
    decision = audit_output.get("deployment_decision", {}) or {}
    risks = _safe_list(audit_output.get("key_risks", []))
    findings = _safe_list(audit_output.get("findings", []))
    missing_controls = _safe_list(audit_output.get("missing_controls", []))
    missing_evidence = _safe_list(audit_output.get("missing_evidence", []))
    roadmap = audit_output.get("remediation_roadmap", {}) or {}
    confidence = audit_output.get("confidence_assessment", {}) or {}
    entity_profile = audit_output.get("entity_profile", {}) or {}

    entity_name = (
        entity_profile.get("legal_name")
        or entity_profile.get("entity_name")
        or executive.get("system_or_business_reviewed")
        or ""
    )

    historical_context = build_historical_context(str(entity_name))

    board_memo = {
        "title": "Board Memo",
        "overall_readiness": executive.get("overall_readiness", ""),
        "decision_summary": executive.get("decision_summary", ""),
        "top_issues": executive.get("top_issues", []),
        "top_risks": [r.get("risk_title", "") for r in risks[:5]],
        "board_message": executive.get("board_message", ""),
        "historical_context": {
            "label": "Prior / Historical Context",
            "has_history": historical_context.get("has_history", False),
            "prior_decision_trajectory": historical_context.get("prior_decision_trajectory", {}),
            "prior_remediation_trajectory": historical_context.get("prior_remediation_trajectory", {}),
            "prior_recurring_missing_controls": historical_context.get("prior_recurring_missing_controls", []),
            "repeated_governance_weaknesses": historical_context.get("repeated_governance_weaknesses", []),
            "repeated_screening_weaknesses": historical_context.get("repeated_screening_weaknesses", []),
            "repeated_licensing_weaknesses": historical_context.get("repeated_licensing_weaknesses", []),
            "repeated_remediation_weaknesses": historical_context.get("repeated_remediation_weaknesses", []),
        },
    }

    regulator_memo = {
        "title": "Regulator Memo",
        "decision": decision.get("status", ""),
        "decision_rationale": decision.get("decision_rationale", ""),
        "blocking_issues": decision.get("blocking_issues", []),
        "missing_controls": [x.get("control_id", "") for x in missing_controls],
        "missing_evidence": [x.get("control_id", "") for x in missing_evidence],
        "historical_context": {
            "label": "Prior / Historical Context",
            "has_history": historical_context.get("has_history", False),
            "prior_recurring_missing_controls": historical_context.get("prior_recurring_missing_controls", []),
            "prior_recurring_findings": historical_context.get("prior_recurring_findings", []),
            "prior_decision_trajectory": historical_context.get("prior_decision_trajectory", {}),
            "prior_remediation_trajectory": historical_context.get("prior_remediation_trajectory", {}),
        },
    }

    client_report = {
        "title": "Client Audit Report",
        "summary": audit_output.get("reporting_outputs", {}).get("client_facing_summary", ""),
        "findings": findings,
        "remediation_roadmap": roadmap,
        "confidence_assessment": confidence,
        "historical_context": {
            "label": "Prior / Historical Context",
            "has_history": historical_context.get("has_history", False),
            "prior_recurring_missing_controls": historical_context.get("prior_recurring_missing_controls", []),
            "prior_recurring_findings": historical_context.get("prior_recurring_findings", []),
            "prior_decision_trajectory": historical_context.get("prior_decision_trajectory", {}),
            "prior_remediation_trajectory": historical_context.get("prior_remediation_trajectory", {}),
        },
    }

    appendix = {
        "title": "Evidence Appendix",
        "evidence_appendix": audit_output.get("evidence_appendix", []),
        "historical_context": {
            "label": "Prior / Historical Context",
            "has_history": historical_context.get("has_history", False),
            "repeated_governance_weaknesses": historical_context.get("repeated_governance_weaknesses", []),
            "repeated_screening_weaknesses": historical_context.get("repeated_screening_weaknesses", []),
            "repeated_licensing_weaknesses": historical_context.get("repeated_licensing_weaknesses", []),
            "repeated_remediation_weaknesses": historical_context.get("repeated_remediation_weaknesses", []),
        },
    }

    return {
        "board_memo": board_memo,
        "regulator_memo": regulator_memo,
        "client_report": client_report,
        "appendix": appendix,
    }
