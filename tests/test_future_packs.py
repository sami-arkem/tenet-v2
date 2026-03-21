from src.core.pack_loader import (
    load_domain_packs,
    load_jurisdiction_packs,
    supported_domains_for_jurisdiction,
    query_seeds_for_domain,
    control_ids_for_domain,
)
from src.core.pack_composer import compose_pack_view


def test_future_jurisdiction_packs_present():
    packs = load_jurisdiction_packs()
    assert "UAE" in packs
    assert "SINGAPORE" in packs
    assert "HONG_KONG" in packs
    assert "CANADA" in packs
    assert "AUSTRALIA" in packs


def test_future_domain_packs_present():
    packs = load_domain_packs()
    assert "fraud" in packs
    assert "transaction_screening" in packs
    assert "regulatory_licensing" in packs
    assert "remediation_tracking" in packs


def test_uae_supports_future_domains():
    domains = supported_domains_for_jurisdiction("UAE")
    assert "fraud" in domains
    assert "transaction_screening" in domains
    assert "regulatory_licensing" in domains
    assert "remediation_tracking" in domains


def test_fraud_domain_has_query_seeds():
    seeds = query_seeds_for_domain("fraud")
    assert "fraud policy" in seeds


def test_transaction_screening_domain_has_controls():
    controls = control_ids_for_domain("transaction_screening")
    assert "SAN-001" in controls
    assert "AML-003" in controls


def test_future_pack_composition_for_uae_sanctions():
    view = compose_pack_view({
        "audit_type": "sanctions_readiness_review",
        "jurisdictions": ["UAE"],
        "domains": ["sanctions", "transaction_screening", "governance"],
    })
    assert "UAE" in view["jurisdictions"]
    assert "transaction_screening" in view["domains"]
    assert "SAN-001" in view["controls"]
    assert "UAE_SANCTIONS_BASELINE" in view["regimes"]
    assert "screening procedure" in " ".join(view["query_seeds"]).lower() or "transaction screening" in " ".join(view["query_seeds"]).lower()
