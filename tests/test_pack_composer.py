from src.core.pack_composer import compose_pack_view


def test_compose_pack_view_for_aml_us():
    view = compose_pack_view({
        "audit_type": "aml_readiness_review",
        "jurisdictions": ["US"],
    })
    assert "US" in view["jurisdictions"]
    assert "aml" in view["domains"]
    assert "AML-003" in view["controls"]
    assert "BSA_AML" in view["regimes"]
    assert "aml policy" in view["query_seeds"]


def test_compose_pack_view_for_sanctions_us_eu():
    view = compose_pack_view({
        "audit_type": "sanctions_readiness_review",
        "jurisdictions": ["US", "EU"],
    })
    assert "sanctions" in view["domains"]
    assert "screening" in view["domains"]
    assert "SAN-001" in view["controls"]
    assert "OFAC" in view["regimes"]
    assert "EU_SANCTIONS" in view["regimes"]


def test_compose_pack_view_for_vendor_global():
    view = compose_pack_view({
        "audit_type": "vendor_internal_compliance_readiness_review",
        "jurisdictions": ["US", "UK", "EU"],
    })
    assert "vendor_risk" in view["domains"]
    assert "VEN-001" in view["controls"]
    assert "THIRD_PARTY_RISK" in view["regimes"]


def test_explicit_domains_are_respected_when_supported():
    view = compose_pack_view({
        "audit_type": "policy_governance_gap_analysis",
        "jurisdictions": ["US"],
        "domains": ["governance", "vendor_risk"],
    })
    assert view["domains"] == ["governance", "vendor_risk"]
