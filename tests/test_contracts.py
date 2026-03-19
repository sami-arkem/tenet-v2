from src.core.contracts import validate_audit_context


def test_validate_audit_context_accepts_valid_input():
    errors = validate_audit_context({
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US", "UK"],
    })
    assert errors == []


def test_validate_audit_context_rejects_invalid_input():
    errors = validate_audit_context({
        "audit_type": "bad_type",
        "industry": "bad_industry",
        "jurisdictions": ["XX"],
    })
    assert errors
