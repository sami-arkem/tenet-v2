from src.core.pack_loader import (
    control_ids_for_domain,
    load_domain_packs,
    load_jurisdiction_packs,
    query_seeds_for_domain,
    supported_domains_for_jurisdiction,
    composed_control_ids,
)


def test_jurisdiction_packs_load():
    packs = load_jurisdiction_packs()
    assert "US" in packs
    assert "UK" in packs
    assert "EU" in packs


def test_domain_packs_load():
    packs = load_domain_packs()
    assert "aml" in packs
    assert "kyc_kyb" in packs
    assert "sanctions" in packs
    assert "governance" in packs
    assert "vendor_risk" in packs
    assert "screening" in packs
    assert "regulatory_reporting" in packs


def test_us_supports_screening():
    domains = supported_domains_for_jurisdiction("US")
    assert "screening" in domains


def test_sanctions_domain_has_controls():
    controls = control_ids_for_domain("sanctions")
    assert "SAN-001" in controls


def test_aml_domain_has_query_seeds():
    seeds = query_seeds_for_domain("aml")
    assert "aml policy" in seeds


def test_composed_controls_are_deduped():
    controls = composed_control_ids(["aml", "sanctions", "governance"])
    assert "AML-001" in controls
    assert "SAN-001" in controls
    assert "GOV-001" in controls
    assert len(controls) == len(set(controls))
