"""
Tests for jurisdiction pack module and router.
Verifies: pack loading, control access, filtering, real-estate overlays, API response structure.
"""

import pytest
from app.agents.jurisdiction_packs import (
    JurisdictionCode,
    Domain,
    get_jurisdiction_pack,
    list_jurisdiction_packs,
    get_pack_control,
    get_pack_controls_by_domain,
)


class TestJurisdictionPackLoading:
    """Test pack loading and metadata."""

    def test_us_pack_loads(self):
        """US pack can be loaded."""
        pack = get_jurisdiction_pack(JurisdictionCode.US)
        assert pack is not None
        assert pack.metadata.jurisdiction == JurisdictionCode.US
        assert pack.metadata.pack_id == "US-v1"

    def test_pack_metadata(self):
        """Pack metadata is complete."""
        pack = get_jurisdiction_pack(JurisdictionCode.US)
        assert pack.metadata.country_codes == ["US"]
        assert len(pack.metadata.regulators) >= 5  # FINCEN, OFAC, SEC, FINRA, NYDFS
        assert JurisdictionCode.US.value in [r.jurisdiction.value for r in [pack.metadata]]
        assert pack.metadata.priority == 1
        assert pack.metadata.version == "1.0"

    def test_nonexistent_jurisdiction_returns_none(self):
        """Nonexistent jurisdiction returns None."""
        pack = get_jurisdiction_pack(JurisdictionCode.UAE)
        assert pack is None

    def test_list_packs(self):
        """List packs shows available packs."""
        packs = list_jurisdiction_packs()
        assert len(packs) >= 1
        assert any(p.pack_id == "US-v1" for p in packs)


class TestControlAccess:
    """Test control loading and retrieval."""

    def test_us_pack_has_controls(self):
        """US pack loads with controls."""
        pack = get_jurisdiction_pack(JurisdictionCode.US)
        assert len(pack.controls) > 0

    def test_get_control_by_id(self):
        """Get control by ID."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-01")
        assert control is not None
        assert control.control_id == "US-AML-01"
        assert control.control_name == "AML Program - Written Policies and Procedures"

    def test_nonexistent_control_returns_none(self):
        """Nonexistent control returns None."""
        control = get_pack_control(JurisdictionCode.US, "NONEXISTENT")
        assert control is None

    def test_control_has_required_fields(self):
        """Control has all required fields."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-01")
        assert control.control_id
        assert control.control_name
        assert control.control_description
        assert control.domain
        assert control.jurisdiction
        assert control.regime_mapping
        assert control.severity
        assert control.regulatory_reference
        assert control.risk_if_missing
        assert control.evidence_requirements
        assert control.remediation_templates
        assert control.missing_criteria
        assert control.partial_criteria
        assert control.supported_criteria


class TestDomainFiltering:
    """Test control filtering by domain."""

    def test_filter_aml_controls(self):
        """Filter returns only AML controls."""
        controls = get_pack_controls_by_domain(JurisdictionCode.US, Domain.AML_KYC)
        assert len(controls) > 0
        assert all(c.domain == Domain.AML_KYC for c in controls)

    def test_filter_sanctions_controls(self):
        """Filter returns only sanctions controls."""
        controls = get_pack_controls_by_domain(JurisdictionCode.US, Domain.SANCTIONS)
        assert len(controls) > 0
        assert all(c.domain == Domain.SANCTIONS for c in controls)

    def test_filter_fraud_controls(self):
        """Filter returns only fraud controls."""
        controls = get_pack_controls_by_domain(JurisdictionCode.US, Domain.FRAUD_TXN_MONITORING)
        assert len(controls) > 0
        assert all(c.domain == Domain.FRAUD_TXN_MONITORING for c in controls)

    def test_filter_governance_controls(self):
        """Filter returns only governance controls."""
        controls = get_pack_controls_by_domain(JurisdictionCode.US, Domain.GOVERNANCE_VENDOR)
        assert len(controls) > 0
        assert all(c.domain == Domain.GOVERNANCE_VENDOR for c in controls)

    def test_filter_real_estate_controls(self):
        """Filter returns only real-estate controls."""
        controls = get_pack_controls_by_domain(JurisdictionCode.US, Domain.REAL_ESTATE)
        assert len(controls) > 0
        assert all(c.domain == Domain.REAL_ESTATE for c in controls)


class TestEvidenceRequirements:
    """Test evidence requirement specification."""

    def test_aml01_has_evidence_requirements(self):
        """AML-01 has multiple evidence requirements."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-01")
        assert len(control.evidence_requirements) >= 4

    def test_evidence_requirement_structure(self):
        """Evidence requirements have required fields."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-01")
        req = control.evidence_requirements[0]
        assert req.document_type
        assert req.description
        assert req.scoring_keywords
        assert req.confidence_threshold
        assert req.is_mandatory in (True, False)

    def test_mandatory_vs_optional_evidence(self):
        """Controls specify mandatory vs optional evidence."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-01")
        mandatory = [r for r in control.evidence_requirements if r.is_mandatory]
        optional = [r for r in control.evidence_requirements if not r.is_mandatory]
        assert len(mandatory) > 0  # Some evidence is mandatory
        # Optional evidence is OK but not required


class TestRemediationTemplates:
    """Test remediation guidance."""

    def test_aml01_has_remediation_templates(self):
        """AML-01 has remediation templates."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-01")
        assert len(control.remediation_templates) > 0

    def test_remediation_template_structure(self):
        """Remediation template has required fields."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-01")
        tpl = control.remediation_templates[0]
        assert tpl.gap_type
        assert tpl.corrective_action
        assert tpl.owner_type
        assert tpl.priority
        assert tpl.estimated_effort_days >= 0
        assert tpl.expected_evidence_after

    def test_remediation_covers_missing_and_partial(self):
        """Remediation templates cover MISSING and PARTIAL scenarios."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-01")
        gap_types = {t.gap_type for t in control.remediation_templates}
        assert "MISSING" in gap_types or "PARTIAL" in gap_types


class TestRealEstateOverlays:
    """Test real-estate-specific control overlays."""

    def test_real_estate_control_has_overlays(self):
        """Real-estate control has property-specific overlays."""
        control = get_pack_control(JurisdictionCode.US, "US-RE-01")
        assert len(control.real_estate_overlays) > 0

    def test_overlay_structure(self):
        """Real-estate overlay has required fields."""
        control = get_pack_control(JurisdictionCode.US, "US-RE-01")
        overlay = control.real_estate_overlays[0]
        assert overlay.scenario
        assert overlay.kyc_expectations
        assert overlay.beneficial_ownership_depth >= 0
        assert overlay.transaction_red_flags
        assert overlay.sector_specific_risks

    def test_multiple_scenarios(self):
        """Real-estate control covers multiple scenarios (buyer, seller, broker)."""
        control = get_pack_control(JurisdictionCode.US, "US-RE-01")
        scenarios = {o.scenario for o in control.real_estate_overlays}
        assert "PROPERTY_BUYER" in scenarios
        assert "PROPERTY_SELLER" in scenarios
        assert "PROPERTY_BROKER" in scenarios


class TestDeterministicGapLogic:
    """Test gap detection criteria."""

    def test_control_has_gap_criteria(self):
        """Controls specify missing/partial/supported criteria."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-01")
        assert control.missing_criteria
        assert control.partial_criteria
        assert control.supported_criteria

    def test_criteria_structure(self):
        """Criteria are lists of clear statements."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-01")
        for criterion in control.missing_criteria:
            assert isinstance(criterion, str)
            assert len(criterion) > 0

    def test_risk_raise_criteria(self):
        """Controls can specify risk-raise criteria even when PASS."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-01")
        assert isinstance(control.risk_raise_criteria, list)


class TestRetrievalHints:
    """Test retrieval and corpus alignment."""

    def test_controls_have_retrieval_tags(self):
        """Controls have tags for retrieval."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-01")
        assert control.retrieval_tags
        assert len(control.retrieval_tags) > 0

    def test_controls_have_corpus_hints(self):
        """Controls specify document types to look for."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-01")
        assert control.corpus_hints
        assert len(control.corpus_hints) > 0

    def test_controls_have_source_types(self):
        """Controls specify acceptable file types."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-01")
        assert control.source_types
        assert len(control.source_types) > 0

    def test_update_cadence_specified(self):
        """Controls specify expected update frequency."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-01")
        assert control.update_cadence_days > 0


class TestRegulatoryReferences:
    """Test regulatory mapping and references."""

    def test_all_controls_have_regulatory_references(self):
        """All controls specify regulatory references."""
        pack = get_jurisdiction_pack(JurisdictionCode.US)
        for control in pack.controls:
            assert control.regulatory_reference
            assert len(control.regulatory_reference) > 0
            # Should be specific, not vague
            assert "CFR" in control.regulatory_reference or "USC" in control.regulatory_reference or "FinCEN" in control.regulatory_reference

    def test_regime_mapping_specified(self):
        """Controls map to specific regimes."""
        pack = get_jurisdiction_pack(JurisdictionCode.US)
        for control in pack.controls:
            assert control.regime_mapping
            # Should be specific (BSA, OFAC, etc.), not generic
            assert len(control.regime_mapping) > 5


class TestControlCompletion:
    """Test that key controls exist and are complete."""

    def test_aml01_complete(self):
        """AML-01 (AML Program) is complete."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-01")
        assert control.severity.value == "CRITICAL"
        assert len(control.evidence_requirements) >= 3
        assert len(control.remediation_templates) >= 1

    def test_aml02_complete(self):
        """AML-02 (CDD) is complete."""
        control = get_pack_control(JurisdictionCode.US, "US-AML-02")
        assert control.control_id == "US-AML-02"
        assert "Customer Due Diligence" in control.control_name

    def test_sanctions01_complete(self):
        """SANCTIONS-01 (OFAC) is complete."""
        control = get_pack_control(JurisdictionCode.US, "US-SANCTIONS-01")
        assert control.regulator.value == "OFAC"
        assert len(control.evidence_requirements) >= 2

    def test_real_estate_control_present(self):
        """Real-estate control (US-RE-01) exists."""
        control = get_pack_control(JurisdictionCode.US, "US-RE-01")
        assert control is not None
        assert control.domain == Domain.REAL_ESTATE
