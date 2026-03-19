import json

from src.reporting.report_prompt_builder import build_report_messages


def test_build_report_messages():
    messages = build_report_messages(
        {"deployment_decision": {"status": "BLOCKED"}},
        {"board_memo": {"title": "Board Memo"}}
    )
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_build_report_messages_includes_templates_and_repair_context():
    messages = build_report_messages(
        {
            "deployment_decision": {"status": "BLOCKED"},
            "entity_profile": {"legal_name": "Test Entity"},
            "findings": [{"title": "Finding A"}],
            "missing_controls": [{"control_id": "AML-001"}],
        },
        {"board_memo": {"title": "Board Memo"}},
        validation_failures=["client_report: missing finding title 'Finding A'"],
        prior_reports={"client_report_markdown": "# Client Report"},
    )
    payload = json.loads(messages[1]["content"])
    assert "templates" in payload
    assert "repair_request" in payload
    assert payload["must_reference"]["entity_name"] == "Test Entity"
    assert "Finding A" in payload["repair_request"]["validation_failures"][0]
