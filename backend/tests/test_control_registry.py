"""
Tests for the Gold Case Control Registry — Bible §11 + §T.1.
"""
import pytest
from app.agents.control_registry import (
    Control,
    Regime,
    Severity,
    get_control,
    get_controls_for_regimes,
    list_all_controls,
    list_regimes,
)


class TestControlRegistry:

    def test_all_controls_loaded(self):
        controls = list_all_controls()
        assert len(controls) >= 20, "Must have at least 20 controls across all regimes"

    def test_no_duplicate_control_ids(self):
        controls = list_all_controls()
        ids = [c.control_id for c in controls]
        assert len(ids) == len(set(ids)), "All control IDs must be unique"

    def test_aml_controls_exist(self):
        controls = get_controls_for_regimes(["AML"])
        assert len(controls) >= 8
        ids = {c.control_id for c in controls}
        for expected in ["AML-01", "AML-02", "AML-03", "AML-04", "AML-05"]:
            assert expected in ids, f"{expected} must be in AML controls"

    def test_gdpr_controls_exist(self):
        controls = get_controls_for_regimes(["GDPR"])
        assert len(controls) >= 4
        ids = {c.control_id for c in controls}
        for expected in ["GDPR-01", "GDPR-02", "GDPR-03"]:
            assert expected in ids

    def test_fca_controls_exist(self):
        controls = get_controls_for_regimes(["FCA"])
        assert len(controls) >= 2

    def test_sanctions_controls_exist(self):
        controls = get_controls_for_regimes(["SANCTIONS"])
        assert len(controls) >= 2

    def test_multiple_regimes_combined(self):
        aml = get_controls_for_regimes(["AML"])
        gdpr = get_controls_for_regimes(["GDPR"])
        combined = get_controls_for_regimes(["AML", "GDPR"])
        assert len(combined) == len(aml) + len(gdpr)

    def test_no_duplicate_controls_in_combined_regimes(self):
        controls = get_controls_for_regimes(["AML", "GDPR", "FCA", "SANCTIONS"])
        ids = [c.control_id for c in controls]
        assert len(ids) == len(set(ids))

    def test_unknown_regime_returns_empty(self):
        controls = get_controls_for_regimes(["UNKNOWN_REGIME"])
        assert controls == []

    def test_get_control_by_id(self):
        ctrl = get_control("AML-01")
        assert ctrl is not None
        assert ctrl.control_id == "AML-01"
        assert ctrl.regime == Regime.AML
        assert ctrl.severity == Severity.CRITICAL

    def test_get_nonexistent_control(self):
        assert get_control("NONEXISTENT-99") is None

    def test_all_controls_have_required_fields(self):
        for ctrl in list_all_controls():
            assert ctrl.control_id, f"control_id missing on {ctrl}"
            assert ctrl.name, f"name missing on {ctrl.control_id}"
            assert ctrl.description, f"description missing on {ctrl.control_id}"
            assert ctrl.regulatory_reference, f"regulatory_reference missing on {ctrl.control_id}"
            assert ctrl.severity in Severity, f"invalid severity on {ctrl.control_id}"
            assert ctrl.regime in Regime, f"invalid regime on {ctrl.control_id}"
            assert len(ctrl.scoring_keywords) >= 5, f"insufficient scoring_keywords on {ctrl.control_id}"
            assert 0.0 < ctrl.pass_threshold <= 1.0
            assert 0.0 < ctrl.partial_threshold <= ctrl.pass_threshold

    def test_list_regimes(self):
        regimes = list_regimes()
        assert "AML" in regimes
        assert "GDPR" in regimes
        assert "FCA" in regimes
        assert "SANCTIONS" in regimes

    def test_critical_controls_all_have_required_evidence(self):
        for ctrl in list_all_controls():
            if ctrl.severity == Severity.CRITICAL:
                assert len(ctrl.required_evidence_types) >= 1, \
                    f"Critical control {ctrl.control_id} must specify required evidence types"

    def test_aml01_is_critical(self):
        ctrl = get_control("AML-01")
        assert ctrl is not None
        assert ctrl.severity == Severity.CRITICAL

    def test_controls_have_gap_and_risk_templates(self):
        # At least all CRITICAL controls must have gap/risk templates
        for ctrl in list_all_controls():
            if ctrl.severity == Severity.CRITICAL:
                assert ctrl.gap_template, f"CRITICAL control {ctrl.control_id} must have gap_template"
                assert ctrl.risk_template, f"CRITICAL control {ctrl.control_id} must have risk_template"
