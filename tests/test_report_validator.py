from src.reporting.report_validator import validate_report_outputs


def test_validate_report_outputs_ok():
    audit_output = {
        "deployment_decision": {"status": "BLOCKED"},
        "entity_profile": {"legal_name": "Test Entity"},
        "findings": [{"title": "Transaction monitoring framework documented"}],
        "missing_controls": [{"control_id": "AML-003"}],
    }
    reports = {
        "board_memo_markdown": "## Board Memo\n\nTest Entity\n\nBLOCKED",
        "regulator_memo_markdown": "## Regulator Memo\n\nTest Entity\n\nBLOCKED\n\nAML-003",
        "client_report_markdown": "# Client Report\n\nTest Entity\n\nBLOCKED\n\nTransaction monitoring framework documented",
    }
    failures = validate_report_outputs(audit_output, reports)
    assert failures == []


def test_validate_report_outputs_catches_drift():
    audit_output = {
        "deployment_decision": {"status": "BLOCKED"},
        "entity_profile": {"legal_name": "Test Entity"},
        "findings": [{"title": "Transaction monitoring framework documented"}],
        "missing_controls": [{"control_id": "AML-003"}],
    }
    reports = {
        "board_memo_markdown": "## Board Memo",
        "regulator_memo_markdown": "## Regulator Memo",
        "client_report_markdown": "# Client Report",
    }
    failures = validate_report_outputs(audit_output, reports)
    assert failures


def test_validate_report_outputs_catches_missing_finding_title():
    audit_output = {
        "deployment_decision": {"status": "BLOCKED"},
        "entity_profile": {"legal_name": "Test Entity"},
        "findings": [{"title": "Enterprise AML policy approved and version controlled"}],
        "missing_controls": [],
    }
    reports = {
        "board_memo_markdown": "## Board Memo\n\nTest Entity\n\nBLOCKED",
        "regulator_memo_markdown": "## Regulator Memo\n\nTest Entity\n\nBLOCKED",
        "client_report_markdown": "# Client Report\n\nTest Entity\n\nBLOCKED\n\nEnterprise AML policy approved and controlled",
    }
    failures = validate_report_outputs(audit_output, reports)
    assert "client_report: missing finding title 'Enterprise AML policy approved and version controlled'" in failures
