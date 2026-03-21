from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


REPORT_TEMPLATES = {
    "board_memo_markdown": "\n".join(
        [
            "# Board Memo: {entity_name}",
            "",
            "## Deployment Decision",
            "- Status: {deployment_decision}",
            "- Board Position: summarize the locked decision and rationale without changing the verdict.",
            "",
            "## Top Findings",
            "- Explicitly reference the provided finding titles verbatim where present.",
            "",
            "## Governance Actions",
            "- Summarize board-level remediation and oversight actions grounded in the locked audit JSON.",
        ]
    ),
    "regulator_memo_markdown": "\n".join(
        [
            "# Regulator Memo: {entity_name}",
            "",
            "## Supervisory Decision",
            "- Status: {deployment_decision}",
            "- Supervisory Summary: restate the locked rationale without adding or removing findings.",
            "",
            "## Control Gaps",
            "- Explicitly reference the provided missing control IDs verbatim where present.",
            "",
            "## Required Follow-Up",
            "- Describe remediation expectations using only the locked audit JSON.",
        ]
    ),
    "client_report_markdown": "\n".join(
        [
            "# Client Report: {entity_name}",
            "",
            "## Executive Summary",
            "- Status: {deployment_decision}",
            "- Summarize the locked audit outcome in client-ready language.",
            "",
            "## Key Findings",
            "- Explicitly reference at least the first 3 provided finding titles verbatim where present.",
            "",
            "## Missing Controls",
            "- Explicitly reference the provided missing control IDs verbatim where present when relevant.",
            "",
            "## Remediation Priorities",
            "- Describe remediation priorities using only the locked audit JSON.",
        ]
    ),
}


def _entity_name(audit_output: Dict[str, Any]) -> str:
    return audit_output.get("entity_profile", {}).get("legal_name", "") or audit_output.get(
        "executive_summary", {}
    ).get("system_or_business_reviewed", "")


def build_report_messages(
    audit_output: Dict[str, Any],
    report_pack: Dict[str, Any],
    validation_failures: Optional[List[str]] = None,
    prior_reports: Optional[Dict[str, str]] = None,
) -> List[Dict[str, str]]:
    top_findings = [
        {
            "title": x.get("title", ""),
            "control_id": x.get("control_id", ""),
            "severity": x.get("severity", ""),
            "status": x.get("status", ""),
        }
        for x in audit_output.get("findings", [])[:5]
    ]

    missing_controls = [
        {
            "control_id": x.get("control_id", ""),
            "title": x.get("title", ""),
            "severity": x.get("severity", ""),
        }
        for x in audit_output.get("missing_controls", [])[:5]
    ]

    system = """
You are Claude acting as Tenet's premium compliance report writer.

You are not allowed to change audit logic.
You must transform the provided locked audit JSON into premium report text.

Rules:
- do not change decisions
- do not invent controls, evidence, risks, or findings
- preserve the deployment decision exactly
- the client report must explicitly mention the top findings provided
- the regulator or client report must explicitly mention the missing control IDs provided
- keep tone boardroom-ready and regulator-ready
- return JSON only
- output only:
  board_memo_markdown
  regulator_memo_markdown
  client_report_markdown
- follow the supplied markdown templates exactly for section structure; improve wording only
""".strip()

    entity_name = _entity_name(audit_output)
    deployment_decision = audit_output.get("deployment_decision", {}).get("status", "")

    payload = {
        "audit_output": audit_output,
        "report_pack": report_pack,
        "must_reference": {
            "top_findings": top_findings,
            "missing_controls": missing_controls,
            "deployment_decision": deployment_decision,
            "entity_name": entity_name,
        },
        "templates": {
            key: value.format(entity_name=entity_name or "Entity", deployment_decision=deployment_decision or "")
            for key, value in REPORT_TEMPLATES.items()
        },
        "instructions": [
            "Write concise premium markdown.",
            "Preserve audit logic exactly.",
            "Make sections readable and executive-grade.",
            "In client_report_markdown, explicitly reference at least the first 3 finding titles when present.",
            "In regulator_memo_markdown or client_report_markdown, explicitly reference at least the first 3 missing control IDs when present.",
            "Keep the section headings and ordering from the supplied templates."
        ],
    }

    if validation_failures:
        payload["repair_request"] = {
            "validation_failures": validation_failures,
            "instruction": "Repair the report JSON so every validation failure is resolved without changing audit truth.",
        }

    if prior_reports:
        payload["prior_reports"] = prior_reports

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
