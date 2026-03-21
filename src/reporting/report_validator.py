from __future__ import annotations

from typing import Any, Dict, List


class ReportValidationError(RuntimeError):
    pass


REQUIRED_REPORT_KEYS = {
    "board_memo_markdown",
    "regulator_memo_markdown",
    "client_report_markdown",
}


def _require_substrings(text: str, required: List[str], label: str) -> List[str]:
    failures: List[str] = []
    lowered = text.lower()
    for item in required:
        if item and item.lower() not in lowered:
            failures.append(f"{label}: missing required text '{item}'")
    return failures


def validate_report_outputs(audit_output: Dict[str, Any], reports: Dict[str, str]) -> List[str]:
    failures: List[str] = []

    missing_keys = REQUIRED_REPORT_KEYS - set(reports.keys())
    if missing_keys:
        failures.append(f"missing report keys: {sorted(missing_keys)}")
        return failures

    board = reports["board_memo_markdown"]
    regulator = reports["regulator_memo_markdown"]
    client = reports["client_report_markdown"]

    decision = audit_output.get("deployment_decision", {}).get("status", "")
    entity_name = audit_output.get("entity_profile", {}).get("legal_name", "") or audit_output.get("executive_summary", {}).get("system_or_business_reviewed", "")
    finding_titles = [x.get("title", "") for x in audit_output.get("findings", [])[:5]]
    missing_control_ids = [x.get("control_id", "") for x in audit_output.get("missing_controls", [])[:5]]

    failures.extend(_require_substrings(board, ["board", decision], "board_memo"))
    failures.extend(_require_substrings(regulator, ["regulator", decision], "regulator_memo"))
    failures.extend(_require_substrings(client, ["report", decision], "client_report"))

    if entity_name:
        failures.extend(_require_substrings(board, [entity_name], "board_memo"))
        failures.extend(_require_substrings(regulator, [entity_name], "regulator_memo"))
        failures.extend(_require_substrings(client, [entity_name], "client_report"))

    for title in finding_titles[:3]:
        if title:
            if title.lower() not in client.lower():
                failures.append(f"client_report: missing finding title '{title}'")

    for control_id in missing_control_ids[:3]:
        if control_id:
            if control_id.lower() not in regulator.lower() and control_id.lower() not in client.lower():
                failures.append(f"reports: missing control reference '{control_id}'")

    return failures


def assert_valid_report_outputs(audit_output: Dict[str, Any], reports: Dict[str, str]) -> None:
    failures = validate_report_outputs(audit_output, reports)
    if failures:
        raise ReportValidationError(" | ".join(failures))
