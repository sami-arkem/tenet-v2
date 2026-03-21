"""
Jurisdiction pack type definitions — shared across all packs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class JurisdictionCode(str, Enum):
    """Country/region codes per rollout order."""
    US = "US"
    UAE = "UAE"
    EU = "EU"
    GB = "GB"
    SG = "SG"
    HK = "HK"
    AU = "AU"
    CA = "CA"
    IN = "IN"
    MX = "MX"
    BR = "BR"
    ZA = "ZA"


class Regulator(str, Enum):
    """Global regulator identifiers."""
    # US
    FINCEN = "FINCEN"
    OFAC = "OFAC"
    SEC = "SEC"
    FINRA = "FINRA"
    NYDFS = "NYDFS"

    # UAE
    CBUAE = "CBUAE"
    DFSA = "DFSA"
    ADGM = "ADGM"
    DIFC = "DIFC"

    # EU
    EBA = "EBA"
    ESMA = "ESMA"
    EDPB = "EDPB"

    # Singapore
    MAS = "MAS"
    PDPC = "PDPC"

    # Hong Kong
    SFC = "SFC"
    HKMA = "HKMA"
    PCPD = "PCPD"

    # Australia
    AUSTRAC = "AUSTRAC"
    ASIC = "ASIC"
    OAIC = "OAIC"

    # Canada
    FINTRAC = "FINTRAC"
    OSFI = "OSFI"
    OPC = "OPC"

    # India
    FIU = "FIU"
    RBI = "RBI"
    NISM = "NISM"


class Domain(str, Enum):
    """Compliance domains per rollout order."""
    AML_KYC = "AML_KYC"
    SANCTIONS = "SANCTIONS"
    FRAUD_TXN_MONITORING = "FRAUD_TXN_MONITORING"
    GOVERNANCE_VENDOR = "GOVERNANCE_VENDOR"
    LICENSING_FILINGS = "LICENSING_FILINGS"
    PRIVACY_DATA = "PRIVACY_DATA"
    TAX_FINANCE = "TAX_FINANCE"
    REAL_ESTATE = "REAL_ESTATE"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class EvidenceRequirement:
    """Evidence requirement specification for a control."""
    document_type: str
    description: str
    scoring_keywords: list[str]
    confidence_threshold: float
    is_mandatory: bool
    examples: list[str] = field(default_factory=list)


@dataclass
class RemediationTemplate:
    """Concrete corrective action guidance."""
    gap_type: str
    corrective_action: str
    owner_type: str
    priority: str
    estimated_effort_days: int
    expected_evidence_after: list[str]
    dependencies: list[str] = field(default_factory=list)


@dataclass
class RealEstateOverlay:
    """Real-estate-specific control variations."""
    scenario: str
    kyc_expectations: str
    source_of_funds_check: bool
    beneficial_ownership_depth: int
    transaction_red_flags: list[str]
    sector_specific_risks: list[str]


@dataclass
class JurisdictionControl:
    """A control as it exists in a specific jurisdiction."""
    control_id: str
    control_name: str
    control_description: str
    domain: Domain
    jurisdiction: JurisdictionCode
    regulator: Optional[Regulator]
    regime_mapping: str
    severity: Severity
    regulatory_reference: str
    risk_if_missing: str

    evidence_requirements: list[EvidenceRequirement]
    remediation_templates: list[RemediationTemplate]

    missing_criteria: list[str]
    partial_criteria: list[str]
    supported_criteria: list[str]
    risk_raise_criteria: list[str]

    real_estate_overlays: list[RealEstateOverlay] = field(default_factory=list)

    retrieval_tags: list[str] = field(default_factory=list)
    corpus_hints: list[str] = field(default_factory=list)
    source_types: list[str] = field(default_factory=list)
    update_cadence_days: int = 365


@dataclass
class JurisdictionPackMetadata:
    """Metadata for a jurisdiction compliance pack."""
    pack_id: str
    jurisdiction: JurisdictionCode
    country_codes: list[str]
    regulators: list[Regulator]
    domains: list[Domain]
    version: str
    source_references: list[str]
    effective_date: Optional[str]
    priority: int
    applicability_notes: str


@dataclass
class JurisdictionPack:
    """A complete jurisdiction compliance pack."""
    metadata: JurisdictionPackMetadata
    controls: list[JurisdictionControl]

    def get_controls_by_domain(self, domain: Domain) -> list[JurisdictionControl]:
        """Filter controls by domain."""
        return [c for c in self.controls if c.domain == domain]

    def get_control(self, control_id: str) -> Optional[JurisdictionControl]:
        """Get single control by ID."""
        for c in self.controls:
            if c.control_id == control_id:
                return c
        return None

    def get_all_control_ids(self) -> list[str]:
        """List all control IDs in this pack."""
        return [c.control_id for c in self.controls]
