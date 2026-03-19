from __future__ import annotations

from typing import Any, Dict, List


def _entity_name(audit_output: Dict[str, Any]) -> str:
    return audit_output.get("entity_profile", {}).get("legal_name", "") or audit_output.get(
        "executive_summary", {}
    ).get("system_or_business_reviewed", "") or "Entity"


def _decision_status(audit_output: Dict[str, Any]) -> str:
    return str(audit_output.get("deployment_decision", {}).get("status", "") or "")


def _finding_titles(audit_output: Dict[str, Any], limit: int = 5) -> List[str]:
    return [str(item.get("title", "") or "") for item in audit_output.get("findings", [])[:limit] if item.get("title")]


def _missing_control_ids(audit_output: Dict[str, Any], limit: int = 5) -> List[str]:
    return [
        str(item.get("control_id", "") or "")
        for item in audit_output.get("missing_controls", [])[:limit]
        if item.get("control_id")
    ]


def build_deterministic_report_outputs(audit_output: Dict[str, Any]) -> Dict[str, str]:
    entity_name = _entity_name(audit_output)
    decision = _decision_status(audit_output)
    finding_titles = _finding_titles(audit_output)
    missing_control_ids = _missing_control_ids(audit_output)

    board_lines = [
        f"# Board Memo: {entity_name}",
        "",
        "## Deployment Decision",
        f"- Status: {decision}",
        "",
        "## Top Findings",
    ]
    board_lines.extend(f"- {title}" for title in finding_titles[:5] or ["No material findings listed in locked audit output."])

    regulator_lines = [
        f"# Regulator Memo: {entity_name}",
        "",
        "## Supervisory Decision",
        f"- Status: {decision}",
        "",
        "## Control Gaps",
    ]
    regulator_lines.extend(
        f"- {control_id}" for control_id in missing_control_ids[:5] or ["No missing control IDs listed in locked audit output."]
    )

    client_lines = [
        f"# Client Report: {entity_name}",
        "",
        "## Executive Summary",
        f"- Status: {decision}",
        "",
        "## Key Findings",
    ]
    client_lines.extend(f"- {title}" for title in finding_titles[:5] or ["No material findings listed in locked audit output."])
    client_lines.extend(
        [
            "",
            "## Missing Controls",
        ]
    )
    client_lines.extend(
        f"- {control_id}" for control_id in missing_control_ids[:5] or ["No missing control IDs listed in locked audit output."]
    )

    return {
        "board_memo_markdown": "\n".join(board_lines).strip() + "\n",
        "regulator_memo_markdown": "\n".join(regulator_lines).strip() + "\n",
        "client_report_markdown": "\n".join(client_lines).strip() + "\n",
    }
