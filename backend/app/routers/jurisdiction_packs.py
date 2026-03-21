"""
Jurisdiction Packs Router — Bible §11.5
Serves jurisdiction-specific compliance frameworks and controls.

Endpoints:
- GET /v1/jurisdiction-packs — List all packs
- GET /v1/jurisdiction-packs/{jurisdiction} — Get pack metadata
- GET /v1/jurisdiction-packs/{jurisdiction}/controls — List controls by jurisdiction
- GET /v1/jurisdiction-packs/{jurisdiction}/controls/{control_id} — Get single control
- GET /v1/jurisdiction-packs/{jurisdiction}/controls?domain={domain} — Filter by domain
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.schemas.response import ApiResponse

from app.agents.jurisdiction_packs import (
    Domain,
    JurisdictionCode,
    Regulator,
    get_jurisdiction_pack,
    list_jurisdiction_packs,
    get_pack_control,
    get_pack_controls_by_domain,
)

router = APIRouter()


# ─── Response Models ─────────────────────────────────────────────────────────


class PackMetadataResponse(BaseModel):
    pack_id: str
    jurisdiction: str
    country_codes: list[str]
    regulators: list[str]
    domains: list[str]
    version: str
    effective_date: str | None
    priority: int
    applicability_notes: str


class EvidenceRequirementResponse(BaseModel):
    document_type: str
    description: str
    scoring_keywords: list[str]
    confidence_threshold: float
    is_mandatory: bool
    examples: list[str]


class RemediationTemplateResponse(BaseModel):
    gap_type: str
    corrective_action: str
    owner_type: str
    priority: str
    estimated_effort_days: int
    expected_evidence_after: list[str]
    dependencies: list[str]


class RealEstateOverlayResponse(BaseModel):
    scenario: str
    kyc_expectations: str
    source_of_funds_check: bool
    beneficial_ownership_depth: int
    transaction_red_flags: list[str]
    sector_specific_risks: list[str]


class JurisdictionControlResponse(BaseModel):
    control_id: str
    control_name: str
    control_description: str
    domain: str
    jurisdiction: str
    regulator: str | None
    regime_mapping: str
    severity: str
    regulatory_reference: str
    risk_if_missing: str
    evidence_requirements: list[EvidenceRequirementResponse]
    remediation_templates: list[RemediationTemplateResponse]
    missing_criteria: list[str]
    partial_criteria: list[str]
    supported_criteria: list[str]
    risk_raise_criteria: list[str]
    real_estate_overlays: list[RealEstateOverlayResponse]
    retrieval_tags: list[str]
    corpus_hints: list[str]
    source_types: list[str]
    update_cadence_days: int


class JurisdictionPackDetailResponse(BaseModel):
    metadata: PackMetadataResponse
    controls: list[JurisdictionControlResponse]


class JurisdictionPackSummaryResponse(BaseModel):
    pack_id: str
    jurisdiction: str
    version: str
    control_count: int
    domains: list[str]


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _control_to_response(control) -> JurisdictionControlResponse:
    """Convert JurisdictionControl to response model."""
    return JurisdictionControlResponse(
        control_id=control.control_id,
        control_name=control.control_name,
        control_description=control.control_description,
        domain=control.domain.value,
        jurisdiction=control.jurisdiction.value,
        regulator=control.regulator.value if control.regulator else None,
        regime_mapping=control.regime_mapping,
        severity=control.severity.value,
        regulatory_reference=control.regulatory_reference,
        risk_if_missing=control.risk_if_missing,
        evidence_requirements=[
            EvidenceRequirementResponse(
                document_type=req.document_type,
                description=req.description,
                scoring_keywords=req.scoring_keywords,
                confidence_threshold=req.confidence_threshold,
                is_mandatory=req.is_mandatory,
                examples=req.examples,
            )
            for req in control.evidence_requirements
        ],
        remediation_templates=[
            RemediationTemplateResponse(
                gap_type=tpl.gap_type,
                corrective_action=tpl.corrective_action,
                owner_type=tpl.owner_type,
                priority=tpl.priority,
                estimated_effort_days=tpl.estimated_effort_days,
                expected_evidence_after=tpl.expected_evidence_after,
                dependencies=tpl.dependencies,
            )
            for tpl in control.remediation_templates
        ],
        missing_criteria=control.missing_criteria,
        partial_criteria=control.partial_criteria,
        supported_criteria=control.supported_criteria,
        risk_raise_criteria=control.risk_raise_criteria,
        real_estate_overlays=[
            RealEstateOverlayResponse(
                scenario=overlay.scenario,
                kyc_expectations=overlay.kyc_expectations,
                source_of_funds_check=overlay.source_of_funds_check,
                beneficial_ownership_depth=overlay.beneficial_ownership_depth,
                transaction_red_flags=overlay.transaction_red_flags,
                sector_specific_risks=overlay.sector_specific_risks,
            )
            for overlay in control.real_estate_overlays
        ],
        retrieval_tags=control.retrieval_tags,
        corpus_hints=control.corpus_hints,
        source_types=control.source_types,
        update_cadence_days=control.update_cadence_days,
    )


def _pack_to_response(pack) -> JurisdictionPackDetailResponse:
    """Convert JurisdictionPack to response model."""
    return JurisdictionPackDetailResponse(
        metadata=PackMetadataResponse(
            pack_id=pack.metadata.pack_id,
            jurisdiction=pack.metadata.jurisdiction.value,
            country_codes=pack.metadata.country_codes,
            regulators=[r.value for r in pack.metadata.regulators],
            domains=[d.value for d in pack.metadata.domains],
            version=pack.metadata.version,
            effective_date=pack.metadata.effective_date,
            priority=pack.metadata.priority,
            applicability_notes=pack.metadata.applicability_notes,
        ),
        controls=[_control_to_response(c) for c in pack.controls],
    )


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.get("", tags=["jurisdiction-packs"])
async def list_packs() -> dict:
    """
    List all available jurisdiction packs.

    Returns: List of pack summaries with metadata.
    """
    packs = list_jurisdiction_packs()
    response = []
    for pack_meta in packs:
        pack = get_jurisdiction_pack(pack_meta.jurisdiction)
        if pack:
            response.append(
                JurisdictionPackSummaryResponse(
                    pack_id=pack.metadata.pack_id,
                    jurisdiction=pack.metadata.jurisdiction.value,
                    version=pack.metadata.version,
                    control_count=len(pack.controls),
                    domains=[d.value for d in pack.metadata.domains],
                ).model_dump()
            )
    return ApiResponse.success(data=response).model_dump()


@router.get("/{jurisdiction}", tags=["jurisdiction-packs"])
async def get_pack(jurisdiction: str) -> dict:
    """
    Get full jurisdiction pack with all controls and evidence requirements.
    """
    try:
        jurisdiction_code = JurisdictionCode(jurisdiction.upper())
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Jurisdiction '{jurisdiction}' not found")

    pack = get_jurisdiction_pack(jurisdiction_code)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Jurisdiction pack '{jurisdiction}' not available")

    return ApiResponse.success(data=_pack_to_response(pack).model_dump()).model_dump()


@router.get("/{jurisdiction}/controls", tags=["jurisdiction-packs"])
async def get_controls(
    jurisdiction: str,
    domain: str | None = Query(None),
) -> dict:
    """Get controls for a jurisdiction, optionally filtered by domain."""
    try:
        jurisdiction_code = JurisdictionCode(jurisdiction.upper())
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Jurisdiction '{jurisdiction}' not found")

    pack = get_jurisdiction_pack(jurisdiction_code)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Jurisdiction pack '{jurisdiction}' not available")

    if domain:
        try:
            domain_enum = Domain(domain.upper())
            controls = get_pack_controls_by_domain(jurisdiction_code, domain_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid domain '{domain}'")
    else:
        controls = pack.controls

    return ApiResponse.success(
        data=[_control_to_response(c).model_dump() for c in controls]
    ).model_dump()


@router.get("/{jurisdiction}/controls/{control_id}", tags=["jurisdiction-packs"])
async def get_control(jurisdiction: str, control_id: str) -> JurisdictionControlResponse:
    """
    Get a single control by jurisdiction and control ID.

    Args:
        jurisdiction: Jurisdiction code (e.g., "US", "UAE", "EU")
        control_id: Control ID (e.g., "US-AML-01", "US-SANCTIONS-01")

    Returns: Complete control specification including evidence requirements, remediation, overlays.

    Raises:
        404: Jurisdiction pack or control not found.
    """
    try:
        jurisdiction_code = JurisdictionCode(jurisdiction.upper())
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Jurisdiction '{jurisdiction}' not found")

    control = get_pack_control(jurisdiction_code, control_id.upper())
    if not control:
        raise HTTPException(status_code=404, detail=f"Control '{control_id}' not found in '{jurisdiction}' pack")

    return ApiResponse.success(data=_control_to_response(control).model_dump()).model_dump()
