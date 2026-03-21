from src.reporting.build_report_pack import build_report_pack
from src.reporting.deterministic_report_builder import build_deterministic_report_markdown_bundle


def _audit_output(entity_name: str = "Definitely Missing Entity"):
    return {
        "entity_profile": {"legal_name": entity_name},
        "executive_summary": {
            "overall_readiness": "Needs work",
            "decision_summary": "Current audit decision is BLOCKED.",
            "top_issues": ["Transaction monitoring gap"],
            "system_or_business_reviewed": entity_name,
        },
        "deployment_decision": {
            "status": "BLOCKED",
            "decision_rationale": "Critical control gap remains",
            "blocking_issues": ["AML-003 not evidenced"],
        },
        "findings": [
            {"title": "Transaction monitoring framework documented", "control_id": "AML-003", "severity": "HIGH"}
        ],
        "missing_controls": [
            {"control_id": "AML-003", "title": "Transaction Monitoring"}
        ],
        "missing_evidence": [
            {"control_id": "AML-003"}
        ],
        "remediation_roadmap": {
            "immediate_0_30_days": ["Implement transaction monitoring policy and workflow"]
        },
        "confidence_assessment": {},
        "reporting_outputs": {"client_facing_summary": "Client-facing summary"},
        "evidence_appendix": [],
    }


def test_report_pack_contains_historical_context_labels():
    pack = build_report_pack(_audit_output())
    assert "historical_context" in pack["board_memo"]
    assert pack["board_memo"]["historical_context"]["label"] == "Prior / Historical Context"
    assert "historical_context" in pack["regulator_memo"]
    assert "historical_context" in pack["client_report"]


def test_deterministic_reports_include_historical_section_without_changing_current_truth():
    reports = build_deterministic_report_markdown_bundle(_audit_output())
    assert "Prior / Historical Context" in reports["board_memo_markdown"]
    assert "Deployment Decision: BLOCKED" in reports["board_memo_markdown"]
    assert "AML-003" in reports["regulator_memo_markdown"]
    assert "Transaction monitoring framework documented" in reports["client_report_markdown"]
