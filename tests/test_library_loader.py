from src.core.library_loader import (
    control_ids_for_audit_type,
    regime_ids_for_audit_type_and_jurisdictions,
    load_control_library,
    load_regime_library,
)


def test_control_library_non_empty():
    data = load_control_library()
    assert "controls" in data
    assert len(data["controls"]) >= 8


def test_regime_library_non_empty():
    data = load_regime_library()
    assert "regimes" in data
    assert len(data["regimes"]) >= 8


def test_aml_audit_maps_to_controls():
    controls = control_ids_for_audit_type("aml_readiness_review")
    assert len(controls) > 0
    assert "AML-003" in controls


def test_sanctions_audit_maps_to_regimes():
    regimes = regime_ids_for_audit_type_and_jurisdictions("sanctions_readiness_review", ["US", "EU"])
    assert "OFAC" in regimes
    assert "EU_SANCTIONS" in regimes


def test_vendor_review_maps_to_controls():
    controls = control_ids_for_audit_type("vendor_internal_compliance_readiness_review")
    assert "VEN-001" in controls
    assert "GOV-001" in controls
