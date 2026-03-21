from src.reasoning.decision import decide_deployment


def test_decide_deployment_blocked_on_critical_missing():
    result = decide_deployment([
        {"severity_if_missing": "critical", "status": "missing", "confidence": 0.9},
        {"severity_if_missing": "high", "status": "met", "confidence": 0.8},
    ])
    assert result["decision"] == "BLOCKED"


def test_decide_deployment_approved_when_controls_are_strong():
    result = decide_deployment([
        {"severity_if_missing": "critical", "status": "met", "confidence": 0.9},
        {"severity_if_missing": "high", "status": "met", "confidence": 0.85},
    ])
    assert result["decision"] == "APPROVED"
