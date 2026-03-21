"""
Comprehensive test suite for all 8 jurisdiction compliance packs.
Tests structure, completeness, and validity of all controls across jurisdictions.
"""

import pytest
from app.agents.jurisdiction_packs import (
    JurisdictionCode,
    Domain,
    Severity,
    get_jurisdiction_pack,
    list_jurisdiction_packs,
)


class TestJurisdictionPackRegistry:
    """Test jurisdiction pack registry and discovery."""

    def test_list_all_packs(self):
        """Test that all 8 packs are listed in registry."""
        packs = list_jurisdiction_packs()
        assert len(packs) == 8, f"Expected 8 packs, got {len(packs)}"

        pack_jurisdictions = {p.jurisdiction for p in packs}
        expected = {
            JurisdictionCode.US,
            JurisdictionCode.UAE,
            JurisdictionCode.EU,
            JurisdictionCode.SG,
            JurisdictionCode.HK,
            JurisdictionCode.AU,
            JurisdictionCode.CA,
            JurisdictionCode.IN,
        }
        assert pack_jurisdictions == expected

    def test_get_each_pack(self):
        """Test that each jurisdiction pack can be loaded."""
        jurisdictions = [
            JurisdictionCode.US,
            JurisdictionCode.UAE,
            JurisdictionCode.EU,
            JurisdictionCode.SG,
            JurisdictionCode.HK,
            JurisdictionCode.AU,
            JurisdictionCode.CA,
            JurisdictionCode.IN,
        ]
        for jurisdiction in jurisdictions:
            pack = get_jurisdiction_pack(jurisdiction)
            assert pack is not None, f"Failed to load {jurisdiction.value} pack"
            assert pack.metadata.jurisdiction == jurisdiction
            assert pack.metadata.pack_id is not None
            assert len(pack.metadata.regulators) > 0

    def test_pack_versions(self):
        """Test that packs are accessible with version specifiers."""
        jurisdictions = [
            JurisdictionCode.US,
            JurisdictionCode.UAE,
            JurisdictionCode.EU,
            JurisdictionCode.SG,
            JurisdictionCode.HK,
            JurisdictionCode.AU,
            JurisdictionCode.CA,
            JurisdictionCode.IN,
        ]
        for jurisdiction in jurisdictions:
            pack_v1 = get_jurisdiction_pack(jurisdiction, version="1.0")
            pack_latest = get_jurisdiction_pack(jurisdiction, version="latest")
            assert pack_v1 is not None
            assert pack_latest is not None
            assert pack_v1.metadata.pack_id == pack_latest.metadata.pack_id


class TestControlStructure:
    """Test control structure and completeness across all packs."""

    @pytest.mark.parametrize("jurisdiction", [
        JurisdictionCode.US,
        JurisdictionCode.UAE,
        JurisdictionCode.EU,
        JurisdictionCode.SG,
        JurisdictionCode.HK,
        JurisdictionCode.AU,
        JurisdictionCode.CA,
        JurisdictionCode.IN,
    ])
    def test_pack_has_18_controls(self, jurisdiction):
        """Test that each pack has exactly 18 controls."""
        pack = get_jurisdiction_pack(jurisdiction)
        assert len(pack.controls) == 18, (
            f"{jurisdiction.value} pack has {len(pack.controls)} controls, "
            f"expected 18"
        )

    @pytest.mark.parametrize("jurisdiction", [
        JurisdictionCode.US,
        JurisdictionCode.UAE,
        JurisdictionCode.EU,
        JurisdictionCode.SG,
        JurisdictionCode.HK,
        JurisdictionCode.AU,
        JurisdictionCode.CA,
        JurisdictionCode.IN,
    ])
    def test_domain_distribution(self, jurisdiction):
        """Test that each pack has correct domain distribution."""
        pack = get_jurisdiction_pack(jurisdiction)

        # Expected distribution: 7 AML/KYC, 2 Sanctions, 2 Fraud, 2 Gov, 2 Licensing, 2 Privacy, 1 Real Estate
        domain_counts = {}
        for control in pack.controls:
            domain = control.domain
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        expected_counts = {
            Domain.AML_KYC: 7,
            Domain.SANCTIONS: 2,
            Domain.FRAUD_TXN_MONITORING: 2,
            Domain.GOVERNANCE_VENDOR: 2,
            Domain.LICENSING_FILINGS: 2,
            Domain.PRIVACY_DATA: 2,
            Domain.REAL_ESTATE: 1,
        }

        assert domain_counts == expected_counts, (
            f"{jurisdiction.value}: Domain distribution mismatch. "
            f"Got {domain_counts}, expected {expected_counts}"
        )

    @pytest.mark.parametrize("jurisdiction", [
        JurisdictionCode.US,
        JurisdictionCode.UAE,
        JurisdictionCode.EU,
        JurisdictionCode.SG,
        JurisdictionCode.HK,
        JurisdictionCode.AU,
        JurisdictionCode.CA,
        JurisdictionCode.IN,
    ])
    def test_control_id_format(self, jurisdiction):
        """Test that control IDs follow correct format."""
        pack = get_jurisdiction_pack(jurisdiction)
        prefix = jurisdiction.value

        for control in pack.controls:
            assert control.control_id.startswith(prefix), (
                f"{jurisdiction.value}: Control ID {control.control_id} "
                f"doesn't start with {prefix}"
            )
            assert "-" in control.control_id, (
                f"{jurisdiction.value}: Control ID {control.control_id} "
                f"doesn't have hyphen separator"
            )

    @pytest.mark.parametrize("jurisdiction", [
        JurisdictionCode.US,
        JurisdictionCode.UAE,
        JurisdictionCode.EU,
        JurisdictionCode.SG,
        JurisdictionCode.HK,
        JurisdictionCode.AU,
        JurisdictionCode.CA,
        JurisdictionCode.IN,
    ])
    def test_all_controls_have_required_fields(self, jurisdiction):
        """Test that all controls have required fields."""
        pack = get_jurisdiction_pack(jurisdiction)

        for control in pack.controls:
            assert control.control_id, f"Control missing control_id"
            assert control.control_name, f"Control {control.control_id} missing name"
            assert control.control_description, f"Control {control.control_id} missing description"
            assert control.domain is not None, f"Control {control.control_id} missing domain"
            assert control.jurisdiction is not None, f"Control {control.control_id} missing jurisdiction"
            assert control.severity is not None, f"Control {control.control_id} missing severity"
            assert control.regulatory_reference, f"Control {control.control_id} missing regulatory_reference"
            assert control.risk_if_missing, f"Control {control.control_id} missing risk_if_missing"


class TestEvidenceRequirements:
    """Test evidence requirements completeness."""

    @pytest.mark.parametrize("jurisdiction", [
        JurisdictionCode.US,
        JurisdictionCode.UAE,
        JurisdictionCode.EU,
        JurisdictionCode.SG,
        JurisdictionCode.HK,
        JurisdictionCode.AU,
        JurisdictionCode.CA,
        JurisdictionCode.IN,
    ])
    def test_all_controls_have_evidence_requirements(self, jurisdiction):
        """Test that all controls have at least 2 evidence requirements."""
        pack = get_jurisdiction_pack(jurisdiction)

        for control in pack.controls:
            assert len(control.evidence_requirements) >= 2, (
                f"{jurisdiction.value} {control.control_id}: "
                f"Has {len(control.evidence_requirements)} evidence requirements, "
                f"expected at least 2"
            )

    @pytest.mark.parametrize("jurisdiction", [
        JurisdictionCode.US,
        JurisdictionCode.UAE,
        JurisdictionCode.EU,
        JurisdictionCode.SG,
        JurisdictionCode.HK,
        JurisdictionCode.AU,
        JurisdictionCode.CA,
        JurisdictionCode.IN,
    ])
    def test_evidence_requirements_have_valid_thresholds(self, jurisdiction):
        """Test that evidence requirements have valid confidence thresholds."""
        pack = get_jurisdiction_pack(jurisdiction)

        for control in pack.controls:
            for evidence in control.evidence_requirements:
                assert 0.0 <= evidence.confidence_threshold <= 1.0, (
                    f"{jurisdiction.value} {control.control_id} {evidence.document_type}: "
                    f"Invalid confidence threshold {evidence.confidence_threshold}"
                )
                # Most mandatory evidence should have reasonably high thresholds (>= 0.70)
                if evidence.is_mandatory:
                    assert evidence.confidence_threshold >= 0.70, (
                        f"{jurisdiction.value} {control.control_id} {evidence.document_type}: "
                        f"Mandatory evidence has low threshold {evidence.confidence_threshold}"
                    )

    @pytest.mark.parametrize("jurisdiction", [
        JurisdictionCode.US,
        JurisdictionCode.UAE,
        JurisdictionCode.EU,
        JurisdictionCode.SG,
        JurisdictionCode.HK,
        JurisdictionCode.AU,
        JurisdictionCode.CA,
        JurisdictionCode.IN,
    ])
    def test_evidence_requirements_have_keywords(self, jurisdiction):
        """Test that all evidence requirements have scoring keywords."""
        pack = get_jurisdiction_pack(jurisdiction)

        for control in pack.controls:
            for evidence in control.evidence_requirements:
                assert len(evidence.scoring_keywords) > 0, (
                    f"{jurisdiction.value} {control.control_id} {evidence.document_type}: "
                    f"No scoring keywords"
                )


class TestRemediationTemplates:
    """Test remediation template completeness."""

    @pytest.mark.parametrize("jurisdiction", [
        JurisdictionCode.US,
        JurisdictionCode.UAE,
        JurisdictionCode.EU,
        JurisdictionCode.SG,
        JurisdictionCode.HK,
        JurisdictionCode.AU,
        JurisdictionCode.CA,
        JurisdictionCode.IN,
    ])
    def test_all_controls_have_remediation_templates(self, jurisdiction):
        """Test that all controls have at least 1 remediation template."""
        pack = get_jurisdiction_pack(jurisdiction)

        for control in pack.controls:
            assert len(control.remediation_templates) >= 1, (
                f"{jurisdiction.value} {control.control_id}: "
                f"Has {len(control.remediation_templates)} remediation templates, "
                f"expected at least 1"
            )

    @pytest.mark.parametrize("jurisdiction", [
        JurisdictionCode.US,
        JurisdictionCode.UAE,
        JurisdictionCode.EU,
        JurisdictionCode.SG,
        JurisdictionCode.HK,
        JurisdictionCode.AU,
        JurisdictionCode.CA,
        JurisdictionCode.IN,
    ])
    def test_remediation_templates_valid_effort(self, jurisdiction):
        """Test that remediation templates have valid effort estimates."""
        pack = get_jurisdiction_pack(jurisdiction)

        for control in pack.controls:
            for template in control.remediation_templates:
                assert 0 < template.estimated_effort_days <= 180, (
                    f"{jurisdiction.value} {control.control_id}: "
                    f"Invalid effort estimate {template.estimated_effort_days} days"
                )


class TestGapLogic:
    """Test gap assessment logic completeness."""

    @pytest.mark.parametrize("jurisdiction", [
        JurisdictionCode.US,
        JurisdictionCode.UAE,
        JurisdictionCode.EU,
        JurisdictionCode.SG,
        JurisdictionCode.HK,
        JurisdictionCode.AU,
        JurisdictionCode.CA,
        JurisdictionCode.IN,
    ])
    def test_all_controls_have_gap_criteria(self, jurisdiction):
        """Test that all controls have at least some gap assessment criteria."""
        pack = get_jurisdiction_pack(jurisdiction)

        for control in pack.controls:
            total_criteria = (
                len(control.missing_criteria) +
                len(control.partial_criteria) +
                len(control.supported_criteria) +
                len(control.risk_raise_criteria)
            )
            assert total_criteria > 0, (
                f"{jurisdiction.value} {control.control_id}: "
                f"No gap assessment criteria defined"
            )


class TestRealEstateOverlays:
    """Test real estate overlays for real estate control."""

    @pytest.mark.parametrize("jurisdiction", [
        JurisdictionCode.US,
        JurisdictionCode.UAE,
        JurisdictionCode.EU,
        JurisdictionCode.SG,
        JurisdictionCode.HK,
        JurisdictionCode.AU,
        JurisdictionCode.CA,
        JurisdictionCode.IN,
    ])
    def test_real_estate_control_has_overlays(self, jurisdiction):
        """Test that real estate control (XX-RE-01) has property overlays."""
        pack = get_jurisdiction_pack(jurisdiction)

        re_controls = [c for c in pack.controls if c.domain == Domain.REAL_ESTATE]
        assert len(re_controls) == 1, (
            f"{jurisdiction.value}: Expected 1 RE control, got {len(re_controls)}"
        )

        re_control = re_controls[0]
        assert len(re_control.real_estate_overlays) >= 3, (
            f"{jurisdiction.value} {re_control.control_id}: "
            f"Has {len(re_control.real_estate_overlays)} overlays, expected at least 3"
        )

    @pytest.mark.parametrize("jurisdiction", [
        JurisdictionCode.US,
        JurisdictionCode.UAE,
        JurisdictionCode.EU,
        JurisdictionCode.SG,
        JurisdictionCode.HK,
        JurisdictionCode.AU,
        JurisdictionCode.CA,
        JurisdictionCode.IN,
    ])
    def test_real_estate_overlays_complete(self, jurisdiction):
        """Test that real estate overlays have complete specifications."""
        pack = get_jurisdiction_pack(jurisdiction)

        re_controls = [c for c in pack.controls if c.domain == Domain.REAL_ESTATE]
        if not re_controls:
            return

        re_control = re_controls[0]
        for overlay in re_control.real_estate_overlays:
            assert overlay.scenario, f"Overlay missing scenario"
            assert overlay.kyc_expectations, f"Overlay missing KYC expectations"
            assert len(overlay.transaction_red_flags) > 0, f"Overlay missing red flags"
            assert len(overlay.sector_specific_risks) > 0, f"Overlay missing sector risks"


class TestMetadata:
    """Test pack metadata completeness."""

    @pytest.mark.parametrize("jurisdiction", [
        JurisdictionCode.US,
        JurisdictionCode.UAE,
        JurisdictionCode.EU,
        JurisdictionCode.SG,
        JurisdictionCode.HK,
        JurisdictionCode.AU,
        JurisdictionCode.CA,
        JurisdictionCode.IN,
    ])
    def test_pack_metadata_valid(self, jurisdiction):
        """Test that pack metadata is complete and valid."""
        pack = get_jurisdiction_pack(jurisdiction)

        assert pack.metadata.pack_id, "Missing pack_id"
        assert pack.metadata.jurisdiction == jurisdiction, "Jurisdiction mismatch"
        assert len(pack.metadata.country_codes) > 0, "Missing country_codes"
        assert len(pack.metadata.regulators) > 0, "Missing regulators"
        assert len(pack.metadata.domains) == 7, f"Expected 7 domains, got {len(pack.metadata.domains)}"
        assert pack.metadata.version, "Missing version"
        assert pack.metadata.priority > 0, "Invalid priority"
        assert pack.metadata.applicability_notes, "Missing applicability_notes"


class TestControlSeverity:
    """Test control severity levels."""

    @pytest.mark.parametrize("jurisdiction", [
        JurisdictionCode.US,
        JurisdictionCode.UAE,
        JurisdictionCode.EU,
        JurisdictionCode.SG,
        JurisdictionCode.HK,
        JurisdictionCode.AU,
        JurisdictionCode.CA,
        JurisdictionCode.IN,
    ])
    def test_severity_assigned(self, jurisdiction):
        """Test that all controls have appropriate severity levels."""
        pack = get_jurisdiction_pack(jurisdiction)

        valid_severities = {Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW}
        for control in pack.controls:
            assert control.severity in valid_severities, (
                f"{jurisdiction.value} {control.control_id}: "
                f"Invalid severity {control.severity}"
            )

    @pytest.mark.parametrize("jurisdiction", [
        JurisdictionCode.US,
        JurisdictionCode.UAE,
        JurisdictionCode.EU,
        JurisdictionCode.SG,
        JurisdictionCode.HK,
        JurisdictionCode.AU,
        JurisdictionCode.CA,
        JurisdictionCode.IN,
    ])
    def test_sanctions_critical_severity(self, jurisdiction):
        """Test that Sanctions controls are CRITICAL severity."""
        pack = get_jurisdiction_pack(jurisdiction)

        for control in pack.controls:
            if control.domain == Domain.SANCTIONS:
                assert control.severity == Severity.CRITICAL, (
                    f"{jurisdiction.value} {control.control_id}: "
                    f"SANCTIONS should be CRITICAL, got {control.severity.value}"
                )
