"""
API tests for jurisdiction packs router.
Tests HTTP endpoints and response serialization.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app, base_url="http://localhost:8000")


class TestJurisdictionPacksListEndpoint:
    """Test GET /v1/jurisdiction-packs"""

    def test_list_packs_success(self, client):
        """List packs returns 200 with pack summaries."""
        response = client.get("/v1/jurisdiction-packs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_response_format(self, client):
        """List response has correct structure."""
        response = client.get("/v1/jurisdiction-packs")
        data = response.json()
        pack = data[0]
        assert "pack_id" in pack
        assert "jurisdiction" in pack
        assert "version" in pack
        assert "control_count" in pack
        assert "domains" in pack

    def test_us_pack_in_list(self, client):
        """US pack appears in list."""
        response = client.get("/v1/jurisdiction-packs")
        data = response.json()
        assert any(p["pack_id"] == "US-v1" for p in data)


class TestGetPackEndpoint:
    """Test GET /v1/jurisdiction-packs/{jurisdiction}"""

    def test_get_us_pack_success(self, client):
        """Get US pack returns 200 with full pack details."""
        response = client.get("/v1/jurisdiction-packs/US")
        assert response.status_code == 200
        data = response.json()
        assert "metadata" in data
        assert "controls" in data

    def test_pack_metadata_structure(self, client):
        """Pack metadata has correct structure."""
        response = client.get("/v1/jurisdiction-packs/US")
        data = response.json()
        metadata = data["metadata"]
        assert metadata["pack_id"] == "US-v1"
        assert metadata["jurisdiction"] == "US"
        assert metadata["version"] == "1.0"
        assert "country_codes" in metadata
        assert "regulators" in metadata
        assert "domains" in metadata

    def test_pack_controls_structure(self, client):
        """Pack controls have correct structure."""
        response = client.get("/v1/jurisdiction-packs/US")
        data = response.json()
        controls = data["controls"]
        assert len(controls) > 0
        control = controls[0]
        assert "control_id" in control
        assert "control_name" in control
        assert "severity" in control
        assert "evidence_requirements" in control
        assert "remediation_templates" in control

    def test_case_insensitive_jurisdiction(self, client):
        """Jurisdiction code is case-insensitive."""
        response_upper = client.get("/v1/jurisdiction-packs/US")
        response_lower = client.get("/v1/jurisdiction-packs/us")
        assert response_upper.status_code == 200
        assert response_lower.status_code == 200
        assert response_upper.json() == response_lower.json()

    def test_invalid_jurisdiction_404(self, client):
        """Invalid jurisdiction returns 404."""
        response = client.get("/v1/jurisdiction-packs/INVALID")
        assert response.status_code == 404

    def test_unavailable_jurisdiction_404(self, client):
        """Unavailable jurisdiction returns 404."""
        response = client.get("/v1/jurisdiction-packs/UAE")
        # UAE pack not implemented yet
        assert response.status_code == 404


class TestGetControlsEndpoint:
    """Test GET /v1/jurisdiction-packs/{jurisdiction}/controls"""

    def test_get_all_controls(self, client):
        """Get all controls for jurisdiction."""
        response = client.get("/v1/jurisdiction-packs/US/controls")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_filter_by_domain(self, client):
        """Filter controls by domain."""
        response = client.get("/v1/jurisdiction-packs/US/controls?domain=AML_KYC")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(c["domain"] == "AML_KYC" for c in data)

    def test_filter_sanctions_domain(self, client):
        """Filter sanctions controls."""
        response = client.get("/v1/jurisdiction-packs/US/controls?domain=SANCTIONS")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(c["domain"] == "SANCTIONS" for c in data)

    def test_filter_real_estate_domain(self, client):
        """Filter real-estate controls."""
        response = client.get("/v1/jurisdiction-packs/US/controls?domain=REAL_ESTATE")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(c["domain"] == "REAL_ESTATE" for c in data)

    def test_invalid_domain_400(self, client):
        """Invalid domain returns 400."""
        response = client.get("/v1/jurisdiction-packs/US/controls?domain=INVALID")
        assert response.status_code == 400

    def test_invalid_jurisdiction_404(self, client):
        """Invalid jurisdiction returns 404."""
        response = client.get("/v1/jurisdiction-packs/INVALID/controls")
        assert response.status_code == 404


class TestGetSingleControlEndpoint:
    """Test GET /v1/jurisdiction-packs/{jurisdiction}/controls/{control_id}"""

    def test_get_aml01_success(self, client):
        """Get AML-01 control returns 200."""
        response = client.get("/v1/jurisdiction-packs/US/controls/US-AML-01")
        assert response.status_code == 200
        data = response.json()
        assert data["control_id"] == "US-AML-01"
        assert "AML Program" in data["control_name"]

    def test_control_detail_structure(self, client):
        """Control detail has complete structure."""
        response = client.get("/v1/jurisdiction-packs/US/controls/US-AML-01")
        data = response.json()
        assert data["control_id"]
        assert data["control_name"]
        assert data["control_description"]
        assert data["domain"]
        assert data["jurisdiction"]
        assert data["severity"]
        assert data["regulatory_reference"]
        assert data["risk_if_missing"]
        assert "evidence_requirements" in data
        assert "remediation_templates" in data
        assert "missing_criteria" in data
        assert "partial_criteria" in data
        assert "supported_criteria" in data
        assert "retrieval_tags" in data

    def test_evidence_requirements_serialized(self, client):
        """Evidence requirements are properly serialized."""
        response = client.get("/v1/jurisdiction-packs/US/controls/US-AML-01")
        data = response.json()
        reqs = data["evidence_requirements"]
        assert len(reqs) > 0
        req = reqs[0]
        assert "document_type" in req
        assert "description" in req
        assert "scoring_keywords" in req
        assert "confidence_threshold" in req
        assert "is_mandatory" in req

    def test_remediation_templates_serialized(self, client):
        """Remediation templates are properly serialized."""
        response = client.get("/v1/jurisdiction-packs/US/controls/US-AML-01")
        data = response.json()
        templates = data["remediation_templates"]
        assert len(templates) > 0
        tpl = templates[0]
        assert "gap_type" in tpl
        assert "corrective_action" in tpl
        assert "owner_type" in tpl
        assert "priority" in tpl

    def test_real_estate_overlays_serialized(self, client):
        """Real-estate overlays are properly serialized."""
        response = client.get("/v1/jurisdiction-packs/US/controls/US-RE-01")
        data = response.json()
        overlays = data["real_estate_overlays"]
        assert len(overlays) > 0
        overlay = overlays[0]
        assert "scenario" in overlay
        assert "kyc_expectations" in overlay
        assert "beneficial_ownership_depth" in overlay
        assert "transaction_red_flags" in overlay

    def test_case_insensitive_control_id(self, client):
        """Control ID is case-insensitive."""
        response_upper = client.get("/v1/jurisdiction-packs/US/controls/US-AML-01")
        response_lower = client.get("/v1/jurisdiction-packs/US/controls/us-aml-01")
        assert response_upper.status_code == 200
        assert response_lower.status_code == 200

    def test_nonexistent_control_404(self, client):
        """Nonexistent control returns 404."""
        response = client.get("/v1/jurisdiction-packs/US/controls/NONEXISTENT")
        assert response.status_code == 404


class TestAPICoverage:
    """Test coverage of key controls via API."""

    def test_aml01_via_api(self, client):
        """AML-01 accessible via API."""
        response = client.get("/v1/jurisdiction-packs/US/controls/US-AML-01")
        assert response.status_code == 200
        data = response.json()
        assert data["severity"] == "CRITICAL"

    def test_aml02_via_api(self, client):
        """AML-02 accessible via API."""
        response = client.get("/v1/jurisdiction-packs/US/controls/US-AML-02")
        assert response.status_code == 200

    def test_sanctions01_via_api(self, client):
        """SANCTIONS-01 accessible via API."""
        response = client.get("/v1/jurisdiction-packs/US/controls/US-SANCTIONS-01")
        assert response.status_code == 200
        data = response.json()
        assert data["regulator"] == "OFAC"

    def test_fraud01_via_api(self, client):
        """FRAUD-01 accessible via API."""
        response = client.get("/v1/jurisdiction-packs/US/controls/US-FRAUD-01")
        assert response.status_code == 200

    def test_governance01_via_api(self, client):
        """GOVERNANCE-01 accessible via API."""
        response = client.get("/v1/jurisdiction-packs/US/controls/US-GOV-01")
        assert response.status_code == 200

    def test_real_estate01_via_api(self, client):
        """REAL_ESTATE-01 accessible via API."""
        response = client.get("/v1/jurisdiction-packs/US/controls/US-RE-01")
        assert response.status_code == 200
        data = response.json()
        assert len(data["real_estate_overlays"]) > 0
