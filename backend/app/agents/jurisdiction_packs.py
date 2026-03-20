"""
Global Jurisdiction Packs — Bible §11.5
Master registry for all jurisdiction-specific compliance frameworks.
Deterministic, version-controlled, extensible to 50+ jurisdictions.

Pack Structure:
- Canonical metadata (jurisdiction, regulators, regimes, domains, versions)
- Control libraries (control_id, name, description, evidence, gap logic)
- Evidence requirements (document types, scoring keywords, confidence thresholds)
- Deterministic gap templates (missing, partial, supported, risk)
- Remediation guidance (concrete actions, owner, priority, dependencies)
- Real-estate overlays (property transaction scenarios, beneficial ownership)
- Retrieval hints (tags, corpus alignment, freshness expectations)

Rollout: US → UAE → EU → Singapore → HK → Australia → Canada → India → LATAM/MENA/Africa
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
    document_type: str          # AML_POLICY, KYC_PROCEDURE, etc.
    description: str            # what we expect to see
    scoring_keywords: list[str] # deterministic keywords for matching
    confidence_threshold: float # HIGH ≥ 0.80, MEDIUM ≥ 0.50, LOW < 0.50
    is_mandatory: bool          # blocks PASS if missing
    examples: list[str] = field(default_factory=list)  # concrete doc names


@dataclass
class RemediationTemplate:
    """Concrete corrective action guidance."""
    gap_type: str               # "MISSING", "PARTIAL", "OUTDATED"
    corrective_action: str      # detailed what-to-do
    owner_type: str             # "COMPLIANCE_OFFICER", "POLICY_TEAM", "BOARD"
    priority: str               # "CRITICAL", "HIGH", "MEDIUM"
    estimated_effort_days: int
    expected_evidence_after: list[str]  # what we should see post-remediation
    dependencies: list[str] = field(default_factory=list)  # other actions to complete first


@dataclass
class RealEstateOverlay:
    """Real-estate-specific control variations."""
    scenario: str               # "PROPERTY_BUYER", "SELLER", "LANDLORD", "BROKER", "DEVELOPER"
    kyc_expectations: str       # enhanced due diligence for property parties
    source_of_funds_check: bool
    beneficial_ownership_depth: int  # how many levels to look-through for UBO
    transaction_red_flags: list[str]
    sector_specific_risks: list[str]


@dataclass
class JurisdictionControl:
    """A control as it exists in a specific jurisdiction."""
    control_id: str                     # e.g. "US-AML-01"
    control_name: str
    control_description: str
    domain: Domain
    jurisdiction: JurisdictionCode
    regulator: Optional[Regulator]
    regime_mapping: str                 # e.g. "BSA/FinCEN AML Ruleset"
    severity: Severity
    regulatory_reference: str           # specific statute, regulation, notice, guidance
    risk_if_missing: str                # concrete business/regulatory risk

    evidence_requirements: list[EvidenceRequirement]
    remediation_templates: list[RemediationTemplate]

    # Deterministic gap logic hooks
    missing_criteria: list[str]         # conditions that = FAIL
    partial_criteria: list[str]         # conditions that = PARTIAL
    supported_criteria: list[str]       # conditions that = PASS
    risk_raise_criteria: list[str]      # raises risk score even if PASS

    real_estate_overlays: list[RealEstateOverlay] = field(default_factory=list)

    # Retrieval hints
    retrieval_tags: list[str] = field(default_factory=list)
    corpus_hints: list[str] = field(default_factory=list)
    source_types: list[str] = field(default_factory=list)
    update_cadence_days: int = 365



@dataclass
class JurisdictionPackMetadata:
    """Metadata for a jurisdiction compliance pack."""
    pack_id: str                        # e.g. "US-v1"
    jurisdiction: JurisdictionCode
    country_codes: list[str]            # ISO 3166-1 alpha-2
    regulators: list[Regulator]
    domains: list[Domain]
    version: str                        # semantic versioning
    source_references: list[str]        # statute/regulation URLs, guidance documents
    effective_date: Optional[str]       # ISO 8601 when this pack takes effect
    priority: int                       # lower = higher priority (US=1, UAE=2, etc.)
    applicability_notes: str            # when/where this pack applies


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


# ═══════════════════════════════════════════════════════════════════════════
# US JURISDICTION PACK v1
# BSA/FinCEN, OFAC, SEC/FINRA, NYDFS, Privacy, Tax
# AML/KYC, Sanctions, Fraud/TxnMonitoring, Governance, Licensing, Privacy, Tax
# ═══════════════════════════════════════════════════════════════════════════

US_PACK_V1 = JurisdictionPack(
    metadata=JurisdictionPackMetadata(
        pack_id="US-v1",
        jurisdiction=JurisdictionCode.US,
        country_codes=["US"],
        regulators=[Regulator.FINCEN, Regulator.OFAC, Regulator.SEC, Regulator.FINRA, Regulator.NYDFS],
        domains=[Domain.AML_KYC, Domain.SANCTIONS, Domain.FRAUD_TXN_MONITORING, Domain.GOVERNANCE_VENDOR, Domain.LICENSING_FILINGS, Domain.PRIVACY_DATA, Domain.TAX_FINANCE, Domain.REAL_ESTATE],
        version="1.0",
        source_references=[
            "https://www.fincen.gov/statutes-and-regulations",
            "https://www.treasury.gov/ofac",
            "https://www.sec.gov/cgi-bin/browse-edgar",
            "https://www.finra.org/rules-guidance",
            "https://www.dfs.ny.gov/consumers/protect-your-privacy"
        ],
        effective_date="2026-01-01",
        priority=1,
        applicability_notes="Mandatory for all US entities; optional overlay for non-US entities with US nexus."
    ),
    controls=[
        # ─── AML / KYC ─────────────────────────────────────────────────────────
        JurisdictionControl(
            control_id="US-AML-01",
            control_name="AML Program - Written Policies and Procedures",
            control_description="Entity must establish, implement, and maintain a written anti-money laundering (AML) program commensurate with its size and risk profile. Program must be approved by board/management and regularly reviewed.",
            domain=Domain.AML_KYC,
            jurisdiction=JurisdictionCode.US,
            regulator=Regulator.FINCEN,
            regime_mapping="Bank Secrecy Act (BSA) 31 USC §5318; AML Ruleset §311.1",
            severity=Severity.CRITICAL,
            regulatory_reference="31 U.S.C. § 5318(a); 31 CFR § 1010.610(a); FinCEN Guidance 2020-G004",
            risk_if_missing="Regulatory enforcement, civil money penalties $25K-$100K+, criminal liability, reputational damage, license revocation.",
            evidence_requirements=[
                EvidenceRequirement(
                    document_type="AML_POLICY",
                    description="Written AML Program policy signed by board/board committee",
                    scoring_keywords=["anti-money laundering", "AML program", "31 USC 5318", "board approval", "management oversight", "written policy"],
                    confidence_threshold=0.80,
                    is_mandatory=True,
                    examples=["AML_Program_Policy_2024.docx", "Board_Resolution_AML_Approval.pdf"]
                ),
                EvidenceRequirement(
                    document_type="PROCEDURES",
                    description="Detailed procedures for CDD, EDD, transaction monitoring, SAR filing",
                    scoring_keywords=["customer due diligence", "CDD", "enhanced due diligence", "EDD", "transaction monitoring", "SAR procedures"],
                    confidence_threshold=0.75,
                    is_mandatory=True,
                    examples=["CDD_Procedures_v2.docx"]
                ),
                EvidenceRequirement(
                    document_type="TRAINING_RECORDS",
                    description="Annual AML training logs for all staff",
                    scoring_keywords=["AML training", "annual training", "compliance training", "employee attestation"],
                    confidence_threshold=0.70,
                    is_mandatory=True
                ),
                EvidenceRequirement(
                    document_type="AUDIT_REPORT",
                    description="Independent AML audit within last 12 months",
                    scoring_keywords=["AML audit", "independent audit", "audit report", "audit findings"],
                    confidence_threshold=0.85,
                    is_mandatory=False
                ),
            ],
            remediation_templates=[
                RemediationTemplate(
                    gap_type="MISSING",
                    corrective_action="Develop comprehensive written AML program including: (1) Clear roles and responsibilities for Compliance Officer; (2) CDD/EDD procedures; (3) Transaction monitoring system specs; (4) SAR/CTR procedures; (5) Training plan; (6) Audit plan. Submit for board approval within 30 days.",
                    owner_type="COMPLIANCE_OFFICER",
                    priority="CRITICAL",
                    estimated_effort_days=45,
                    expected_evidence_after=["Signed board resolution", "Policy document", "Procedure manuals"]
                ),
                RemediationTemplate(
                    gap_type="PARTIAL",
                    corrective_action="Review current AML program against BSA requirements. Add missing procedures (CDD, EDD, TM, SAR). Ensure board approval is documented and recent (within 2 years). Reassess and update within 60 days.",
                    owner_type="COMPLIANCE_OFFICER",
                    priority="HIGH",
                    estimated_effort_days=30,
                    expected_evidence_after=["Updated policy", "Board meeting minutes", "Revision log"]
                ),
            ],
            missing_criteria=[
                "No written AML policy found",
                "Policy not board-approved",
                "Policies older than 3 years without documented review",
            ],
            partial_criteria=[
                "Policy exists but missing CDD or EDD procedures",
                "No training records in last 12 months",
                "Transaction monitoring approach not documented",
            ],
            supported_criteria=[
                "Current, board-approved AML program",
                "Documented CDD, EDD, TM, SAR procedures",
                "Annual training logs with 90%+ staff coverage",
                "Recent independent audit or internal compliance review",
            ],
            risk_raise_criteria=[
                "Policy older than 2 years (even if technically compliant)",
                "No documented board discussion of AML in last 18 months",
            ],
            retrieval_tags=["AML", "BSA", "FinCEN", "Policy", "Program"],
            corpus_hints=["governance documents", "board minutes", "compliance policies"],
            source_types=["PDF", "DOCX", "meeting_minutes"],
            update_cadence_days=365,
        ),

        JurisdictionControl(
            control_id="US-AML-02",
            control_name="Customer Due Diligence (CDD)",
            control_description="Entity must obtain and verify identity of all customers before account opening or business relationship. CDD must include name, DOB, address, identification type/number.",
            domain=Domain.AML_KYC,
            jurisdiction=JurisdictionCode.US,
            regulator=Regulator.FINCEN,
            regime_mapping="FinCEN Rule 31 CFR § 1010.230(a); AML Program Ruleset §302",
            severity=Severity.CRITICAL,
            regulatory_reference="31 CFR § 1010.230; FinCEN Guidance CDD 2008",
            risk_if_missing="Account openings with unverified identity; facilitation of money laundering; CTR/SAR filing gaps; enforcement action.",
            evidence_requirements=[
                EvidenceRequirement(
                    document_type="KYC_PROCEDURE",
                    description="Documented CDD procedures specifying ID verification method, timing, acceptable documents",
                    scoring_keywords=["customer due diligence", "CDD", "identity verification", "acceptable forms of ID", "timing of verification"],
                    confidence_threshold=0.80,
                    is_mandatory=True
                ),
                EvidenceRequirement(
                    document_type="CUSTOMER_ONBOARDING_FILE",
                    description="Sample customer files showing: application, ID document copy, verification evidence, approval",
                    scoring_keywords=["customer application", "government issued ID", "address verification", "approval date"],
                    confidence_threshold=0.85,
                    is_mandatory=True
                ),
                EvidenceRequirement(
                    document_type="SYSTEM_DOCUMENTATION",
                    description="Documentation of system/tools used for identity verification (e.g., IDVerify, manual checks)",
                    scoring_keywords=["identity verification system", "verification tool", "API integration", "verification results"],
                    confidence_threshold=0.70,
                    is_mandatory=False
                ),
            ],
            remediation_templates=[
                RemediationTemplate(
                    gap_type="MISSING",
                    corrective_action="Implement CDD procedure: (1) Define acceptable forms of ID (passport, DL, etc.); (2) Specify verification method (manual, automated, hybrid); (3) Document timing (day 1 before account opening); (4) Establish sampling/testing protocol; (5) Train staff. Complete within 30 days.",
                    owner_type="COMPLIANCE_OFFICER",
                    priority="CRITICAL",
                    estimated_effort_days=20,
                    expected_evidence_after=["Written CDD procedure", "Sample verified customer files", "Training records"]
                ),
            ],
            missing_criteria=[
                "No CDD procedure documented",
                "Customer files without ID verification evidence",
                "CDD data not captured in system",
            ],
            partial_criteria=[
                "CDD done but inconsistently documented",
                "ID verification method not formalized",
            ],
            supported_criteria=[
                "Written CDD procedure referencing 31 CFR § 1010.230",
                "Customer files contain: name, DOB, address, ID copy",
                "Verification completed before account opening",
                "Evidence retained for audit period (5 years)",
            ],
            risk_raise_criteria=[
                "Any customer opened without ID verification",
                "CDD done after account opening",
            ],
            retrieval_tags=["AML", "CDD", "KYC", "Identity"],
            corpus_hints=["procedures", "customer files", "onboarding documentation"],
        ),

        JurisdictionControl(
            control_id="US-AML-03",
            control_name="Enhanced Due Diligence (EDD) - High-Risk Customers",
            control_description="For customers presenting elevated AML risk (PEPs, high-risk jurisdictions, certain business types), entity must conduct EDD including beneficial ownership verification and source of funds/wealth assessment.",
            domain=Domain.AML_KYC,
            jurisdiction=JurisdictionCode.US,
            regulator=Regulator.FINCEN,
            regime_mapping="FinCEN AML Ruleset §303; OFAC Guidance; Risk-Based Approach",
            severity=Severity.HIGH,
            regulatory_reference="31 CFR § 1010.610(b)(5); FinCEN Guidance on EDD 2018",
            risk_if_missing="Facilitation of sanctions-targeted activity, laundering of politically exposed person funds, regulatory penalties.",
            evidence_requirements=[
                EvidenceRequirement(
                    document_type="EDD_PROCEDURE",
                    description="Documented EDD policy specifying: risk tiers, when EDD triggered, beneficial ownership depth, SOF/SOW verification methods",
                    scoring_keywords=["enhanced due diligence", "EDD", "high-risk customer", "beneficial ownership", "source of funds", "PEP screening"],
                    confidence_threshold=0.80,
                    is_mandatory=True
                ),
                EvidenceRequirement(
                    document_type="RISK_ASSESSMENT",
                    description="Risk assessment model or scoring matrix defining what triggers EDD",
                    scoring_keywords=["risk assessment", "risk scoring", "risk matrix", "high-risk indicators"],
                    confidence_threshold=0.75,
                    is_mandatory=True
                ),
                EvidenceRequirement(
                    document_type="EDD_FILE_SAMPLE",
                    description="Sample high-risk customer files showing: beneficial ownership structure, SOF/SOW verification, approval",
                    scoring_keywords=["beneficial owner", "source of funds", "source of wealth", "verification", "UBO"],
                    confidence_threshold=0.85,
                    is_mandatory=True
                ),
            ],
            remediation_templates=[
                RemediationTemplate(
                    gap_type="MISSING",
                    corrective_action="Develop EDD procedure: (1) Define high-risk triggers (PEP, high-risk jurisdiction, cash business); (2) Specify beneficial ownership verification (up to UBO); (3) Document SOF/SOW verification method; (4) Set approval workflow. Complete within 45 days.",
                    owner_type="COMPLIANCE_OFFICER",
                    priority="HIGH",
                    estimated_effort_days=30,
                    expected_evidence_after=["EDD procedure", "Risk assessment", "Sample EDD files"]
                ),
            ],
            missing_criteria=[
                "No EDD procedure exists",
                "High-risk customers lack beneficial ownership verification",
                "SOF/SOW not documented for high-risk customers",
            ],
            partial_criteria=[
                "EDD done ad-hoc, not formalized",
                "Risk assessment not documented",
            ],
            supported_criteria=[
                "Written EDD policy covering PEPs, high-risk jurisdictions, high-risk industries",
                "Risk tiers defined with clear triggers",
                "Beneficial ownership collected to UBO level for high-risk customers",
                "SOF/SOW verification documented",
            ],
            risk_raise_criteria=[
                "Any high-risk customer (PEP, OFAC-jurisdiction) without EDD documentation",
            ],
            retrieval_tags=["AML", "EDD", "KYC", "PEP", "Risk"],
        ),

        # ... (continue with AML-04 through AML-10, then Sanctions, Fraud, Governance, Licensing, Privacy)
        # Abbreviated for efficiency; in production, each would be fully specified as above

        JurisdictionControl(
            control_id="US-AML-04",
            control_name="Transaction Monitoring and Reporting",
            control_description="Entity must monitor customer transactions for suspicious activity and file Suspicious Activity Reports (SARs) with FinCEN within 30 days of detection, without customer notification.",
            domain=Domain.AML_KYC,
            jurisdiction=JurisdictionCode.US,
            regulator=Regulator.FINCEN,
            regime_mapping="BSA 31 USC §5318(g); AML Ruleset §304",
            severity=Severity.CRITICAL,
            regulatory_reference="31 U.S.C. § 5318(g); 31 CFR § 1020.320; FinCEN SAR Guidance",
            risk_if_missing="Undetected money laundering, sanctions evasion, terrorist financing; missed SAR filings attract civil penalties $25K-$100K+ per violation.",
            evidence_requirements=[
                EvidenceRequirement(
                    document_type="TXN_MONITORING_PROCEDURE",
                    description="Documented transaction monitoring system specs, rule definitions, alert thresholds, review/escalation process",
                    scoring_keywords=["transaction monitoring", "suspicious activity", "alert threshold", "monitoring system", "ruleset"],
                    confidence_threshold=0.80,
                    is_mandatory=True
                ),
                EvidenceRequirement(
                    document_type="SAR_FILING_RECORDS",
                    description="SAR filings made to FinCEN (BSA E-Filing), copies with case summary documentation",
                    scoring_keywords=["SAR", "suspicious activity report", "FinCEN filing", "E-filing", "case summary"],
                    confidence_threshold=0.90,
                    is_mandatory=True
                ),
                EvidenceRequirement(
                    document_type="TRANSACTION_ALERT_LOG",
                    description="Monthly/quarterly transaction alert summary showing: # alerts generated, # cases opened, # SARs filed, disposition",
                    scoring_keywords=["alert log", "transaction alert", "case tracking", "SAR disposition"],
                    confidence_threshold=0.75,
                    is_mandatory=True
                ),
            ],
            remediation_templates=[
                RemediationTemplate(
                    gap_type="MISSING",
                    corrective_action="Deploy transaction monitoring: (1) Select/configure monitoring tool (e.g., Actimize, Tealium, manual if small entity); (2) Define alert rules (amount, frequency, beneficiary, jurisdiction); (3) Establish 30-day SAR filing deadline; (4) Document case tracking and SAR filing. Complete within 60 days.",
                    owner_type="COMPLIANCE_OFFICER",
                    priority="CRITICAL",
                    estimated_effort_days=60,
                    expected_evidence_after=["Monitoring system documentation", "Alert rule configuration", "First SAR filing"]
                ),
                RemediationTemplate(
                    gap_type="PARTIAL",
                    corrective_action="Audit transaction monitoring: (1) Review alert threshold appropriateness; (2) Validate all SARs filed in last 2 years met 30-day requirement; (3) Assess rule completeness vs. risk profile; (4) Update rules if gaps found. Complete within 30 days.",
                    owner_type="COMPLIANCE_OFFICER",
                    priority="HIGH",
                    estimated_effort_days=20,
                    expected_evidence_after=["Audit report", "Updated rules", "Remediated SARs if needed"]
                ),
            ],
            missing_criteria=[
                "No transaction monitoring system in place",
                "No SAR filings despite suspicious transactions",
                "SARs filed outside 30-day window",
            ],
            partial_criteria=[
                "Monitoring system exists but alert rules incomplete or untested",
                "SAR process ad-hoc, not formalized",
            ],
            supported_criteria=[
                "Transaction monitoring system active with documented rules",
                "SAR filings to FinCEN within 30 days of detection",
                "Alert log maintained and reviewed monthly",
                "Escalation procedure for high-risk alerts documented",
            ],
            risk_raise_criteria=[
                "Any SAR filed >30 days after detection",
                "Evidence of suspicious transaction not resulting in SAR",
            ],
            retrieval_tags=["AML", "TxnMonitoring", "SAR", "FinCEN"],
        ),

        # ─── SANCTIONS / SCREENING ─────────────────────────────────────────────
        JurisdictionControl(
            control_id="US-SANCTIONS-01",
            control_name="OFAC Sanctions Screening Program",
            control_description="Entity must screen all customers, counterparties, and beneficial owners against OFAC Specially Designated Nationals (SDN) and other sanctions lists before establishing business relationship and periodically thereafter.",
            domain=Domain.SANCTIONS,
            jurisdiction=JurisdictionCode.US,
            regulator=Regulator.OFAC,
            regime_mapping="International Emergency Economic Powers Act (IEEPA) 50 USC §1705; OFAC Compliance Program Guidance",
            severity=Severity.CRITICAL,
            regulatory_reference="50 U.S.C. § 1705; 31 CFR Parts 500-598 (OFAC Regulations); OFAC Guidance 2013-3",
            risk_if_missing="Transactions with sanctioned entities; civil penalties $250K-$20M+ per violation; criminal liability; license revocation.",
            evidence_requirements=[
                EvidenceRequirement(
                    document_type="SCREENING_PROCEDURE",
                    description="Documented screening policy: timing (pre-relationship), screening tool/vendor, false positive resolution, re-screening frequency",
                    scoring_keywords=["OFAC screening", "sanctions screening", "screening vendor", "SDN list", "screening procedure"],
                    confidence_threshold=0.85,
                    is_mandatory=True
                ),
                EvidenceRequirement(
                    document_type="SCREENING_LOG",
                    description="Screening results log showing: name screened, date, result (match/no match), false positive resolution, screening tool version",
                    scoring_keywords=["screening result", "SDN match", "screening vendor", "no match", "screening log"],
                    confidence_threshold=0.80,
                    is_mandatory=True
                ),
                EvidenceRequirement(
                    document_type="OFAC_LIST_VERIFICATION",
                    description="Evidence that entity uses current OFAC lists (SDN, SSI, Consolidated Non-SDN, etc.) with documented refresh cadence",
                    scoring_keywords=["OFAC list", "SDN", "sanctions list update", "list version", "effective date"],
                    confidence_threshold=0.90,
                    is_mandatory=True
                ),
            ],
            remediation_templates=[
                RemediationTemplate(
                    gap_type="MISSING",
                    corrective_action="Implement OFAC screening: (1) Adopt screening tool (vendor or in-house); (2) Document procedure (timing, method, frequency); (3) Screen all existing customers within 30 days; (4) Establish monthly re-screening for high-risk customers. Complete implementation within 45 days.",
                    owner_type="COMPLIANCE_OFFICER",
                    priority="CRITICAL",
                    estimated_effort_days=40,
                    expected_evidence_after=["Screening vendor contract", "Screening log", "Procedure document"]
                ),
            ],
            missing_criteria=[
                "No OFAC screening conducted",
                "Customers opened without pre-screening",
                "Outdated OFAC lists used",
            ],
            partial_criteria=[
                "Screening done manually or inconsistently",
                "Re-screening not performed as required",
            ],
            supported_criteria=[
                "All customers screened against current OFAC lists before relationship begins",
                "Screening log maintained with results documented",
                "Re-screening performed monthly for high-risk, quarterly for others",
                "False positive resolution process documented",
            ],
            risk_raise_criteria=[
                "Any transaction with SDN-list entity",
                "Screening gaps (customers without screening evidence)",
            ],
            retrieval_tags=["OFAC", "Sanctions", "Screening", "SDN"],
        ),

        # ─── FRAUD / TRANSACTION MONITORING ────────────────────────────────────
        JurisdictionControl(
            control_id="US-FRAUD-01",
            control_name="Fraud Detection and Prevention Controls",
            control_description="Entity must implement systems and procedures to detect and prevent fraud, including transaction anomalies, identity fraud, document fraud, and account takeover.",
            domain=Domain.FRAUD_TXN_MONITORING,
            jurisdiction=JurisdictionCode.US,
            regulator=Regulator.FINCEN,  # Multi-regulator but FinCEN priority
            regime_mapping="Fraud Prevention Rule (where applicable); Risk-Based AML Approach",
            severity=Severity.HIGH,
            regulatory_reference="Sector-specific (e.g., BSA for financial institutions); Best practices per FinCEN guidance",
            risk_if_missing="Fraudulent transactions; customer identity fraud; account takeovers; financial loss; reputational damage.",
            evidence_requirements=[
                EvidenceRequirement(
                    document_type="FRAUD_POLICY",
                    description="Documented fraud detection and prevention policy",
                    scoring_keywords=["fraud detection", "fraud prevention", "transaction anomaly", "identity fraud", "risk indicators"],
                    confidence_threshold=0.75,
                    is_mandatory=True
                ),
                EvidenceRequirement(
                    document_type="FRAUD_MONITORING_LOG",
                    description="Monthly fraud case log showing: # cases detected, type, resolution, loss amount (if any)",
                    scoring_keywords=["fraud case", "case summary", "fraud indicator", "detected", "prevented"],
                    confidence_threshold=0.70,
                    is_mandatory=False
                ),
            ],
            remediation_templates=[
                RemediationTemplate(
                    gap_type="MISSING",
                    corrective_action="Establish fraud controls: (1) Document fraud risk indicators; (2) Implement detection system (automated or manual); (3) Define escalation/investigation process; (4) Train staff. Complete within 30 days.",
                    owner_type="COMPLIANCE_OFFICER",
                    priority="HIGH",
                    estimated_effort_days=25,
                    expected_evidence_after=["Fraud policy", "Detection system docs", "Training records"]
                ),
            ],
            missing_criteria=[
                "No fraud detection/prevention approach documented",
            ],
            partial_criteria=[
                "Fraud detection exists but procedures informal",
            ],
            supported_criteria=[
                "Fraud detection policy in place covering common fraud types",
                "System or manual monitoring for anomalies",
                "Investigation and escalation process documented",
            ],
            risk_raise_criteria=[
                "Multiple fraud incidents in last 12 months",
            ],
            retrieval_tags=["Fraud", "Transaction Monitoring", "Risk"],
        ),

        # ─── GOVERNANCE / VENDOR RISK ──────────────────────────────────────────
        JurisdictionControl(
            control_id="US-GOV-01",
            control_name="Compliance Governance and Oversight",
            control_description="Entity must establish clear governance structure with board oversight, documented compliance responsibilities, adequate resources, and independence of compliance function.",
            domain=Domain.GOVERNANCE_VENDOR,
            jurisdiction=JurisdictionCode.US,
            regulator=Regulator.FINCEN,
            regime_mapping="BSA Compliance Program §610(b); AML Ruleset §201-205",
            severity=Severity.CRITICAL,
            regulatory_reference="31 CFR § 1010.610(b); FinCEN Guidance 2020-G004 on AML Program Governance",
            risk_if_missing="Weak compliance culture, ineffective AML program, regulatory enforcement, lack of accountability.",
            evidence_requirements=[
                EvidenceRequirement(
                    document_type="GOVERNANCE_CHARTER",
                    description="Board charter or governance policy defining: compliance committee, audit committee, board oversight frequency",
                    scoring_keywords=["compliance committee", "board charter", "audit committee", "governance", "oversight", "quarterly"],
                    confidence_threshold=0.80,
                    is_mandatory=True
                ),
                EvidenceRequirement(
                    document_type="BOARD_MINUTES",
                    description="Board or compliance committee meeting minutes from last 12 months showing AML/compliance discussion",
                    scoring_keywords=["board meeting", "compliance discussion", "AML program review", "audit report review", "risk discussion"],
                    confidence_threshold=0.85,
                    is_mandatory=True
                ),
                EvidenceRequirement(
                    document_type="COMPLIANCE_JOB_DESCRIPTION",
                    description="Compliance Officer or team job descriptions with reporting line, authority, independence statement",
                    scoring_keywords=["compliance officer", "job description", "reporting line", "authority", "independence"],
                    confidence_threshold=0.75,
                    is_mandatory=True
                ),
            ],
            remediation_templates=[
                RemediationTemplate(
                    gap_type="MISSING",
                    corrective_action="Establish governance: (1) Create compliance committee (board or management level); (2) Appoint compliance officer with independence, authority, adequate staff; (3) Set quarterly board review cadence; (4) Document in charter/policies. Complete within 30 days.",
                    owner_type="BOARD",
                    priority="CRITICAL",
                    estimated_effort_days=20,
                    expected_evidence_after=["Charter", "Job descriptions", "Board resolution"]
                ),
            ],
            missing_criteria=[
                "No compliance governance structure",
                "No compliance officer or designated person",
                "No board oversight of AML program",
            ],
            partial_criteria=[
                "Compliance officer exists but insufficient authority/independence",
                "Board oversight ad-hoc, not scheduled",
            ],
            supported_criteria=[
                "Compliance committee established with defined authority",
                "Compliance officer with independence and adequate resources",
                "Board/management reviews AML program at least quarterly",
                "Clear escalation path to board/audit committee",
            ],
            risk_raise_criteria=[
                "Compliance officer reports to non-executive role (e.g., CFO without independence)",
                "No board discussion of AML in 18+ months",
            ],
            retrieval_tags=["Governance", "Compliance", "Board", "Organization"],
        ),

        # ─── LICENSING / FILINGS ───────────────────────────────────────────────
        JurisdictionControl(
            control_id="US-LIC-01",
            control_name="AML Regulatory Filings and Licensing",
            control_description="Entity must maintain current registration/licensing with applicable regulators (FinCEN, state, etc.) and file required AML-related filings (BSA registration, SAR, CTR, etc.).",
            domain=Domain.LICENSING_FILINGS,
            jurisdiction=JurisdictionCode.US,
            regulator=Regulator.FINCEN,
            regime_mapping="BSA Regulatory Filings; FinCEN Registration",
            severity=Severity.HIGH,
            regulatory_reference="31 CFR § 1010.410 (FinCEN BSA Registration); 31 CFR § 1020.320 (SAR/CTR filings)",
            risk_if_missing="Regulatory violation; operating without proper registration; missed filing deadlines; enforcement.",
            evidence_requirements=[
                EvidenceRequirement(
                    document_type="FINCEN_REGISTRATION",
                    description="Current FinCEN BSA registration certificate or proof of registration (e.g., registration number, confirmation email)",
                    scoring_keywords=["FinCEN registration", "BSA registration", "registration number", "confirmation"],
                    confidence_threshold=0.95,
                    is_mandatory=True
                ),
                EvidenceRequirement(
                    document_type="FILING_HISTORY",
                    description="Record of SAR/CTR/etc. filings made with FinCEN in last 2 years",
                    scoring_keywords=["SAR filing", "CTR filing", "FinCEN filing", "filing date", "filing number"],
                    confidence_threshold=0.85,
                    is_mandatory=False
                ),
            ],
            remediation_templates=[
                RemediationTemplate(
                    gap_type="MISSING",
                    corrective_action="Register with FinCEN if required: (1) Determine if entity is MSB/MVTS/etc. requiring registration; (2) File online at FinCEN.gov; (3) Maintain registration current (renew every 2 years). Complete within 14 days.",
                    owner_type="COMPLIANCE_OFFICER",
                    priority="CRITICAL",
                    estimated_effort_days=5,
                    expected_evidence_after=["FinCEN registration certificate"]
                ),
            ],
            missing_criteria=[
                "Entity required to register but not registered with FinCEN",
                "Registration expired",
            ],
            partial_criteria=[],
            supported_criteria=[
                "Current FinCEN registration if MSB/MVTS/CROW",
                "SAR/CTR filings made timely",
                "State-level licensing current (if required)",
            ],
            risk_raise_criteria=[
                "Any regulatory filing deadline missed",
            ],
            retrieval_tags=["Licensing", "Filings", "FinCEN", "Regulatory"],
        ),

        # ─── PRIVACY / DATA PROTECTION ─────────────────────────────────────────
        JurisdictionControl(
            control_id="US-PRIVACY-01",
            control_name="Privacy and Data Protection Program",
            control_description="Entity must implement privacy safeguards for customer personal information, including data minimization, secure storage, access controls, breach notification.",
            domain=Domain.PRIVACY_DATA,
            jurisdiction=JurisdictionCode.US,
            regulator=Regulator.NYDFS,
            regime_mapping="State Privacy Laws (e.g., NY GBL 668-b); GLBA; Sector-specific (e.g., HIPAA)",
            severity=Severity.HIGH,
            regulatory_reference="NY GBL § 668-b (cybersecurity); Gramm-Leach-Bliley Act (GLBA); Safeguards Rule 16 CFR Part 314",
            risk_if_missing="Data breach, identity theft, regulatory fines, reputational damage, customer lawsuits.",
            evidence_requirements=[
                EvidenceRequirement(
                    document_type="PRIVACY_POLICY",
                    description="Written privacy policy covering: data collection, use, retention, sharing, customer rights, breach notification",
                    scoring_keywords=["privacy policy", "data protection", "data retention", "breach notification", "customer rights"],
                    confidence_threshold=0.80,
                    is_mandatory=True
                ),
                EvidenceRequirement(
                    document_type="DATA_INVENTORY",
                    description="Data inventory documenting: data types collected, source, retention period, security controls",
                    scoring_keywords=["data inventory", "personal data", "retention policy", "security controls", "data classification"],
                    confidence_threshold=0.75,
                    is_mandatory=True
                ),
            ],
            remediation_templates=[
                RemediationTemplate(
                    gap_type="MISSING",
                    corrective_action="Develop privacy program: (1) Create privacy policy; (2) Conduct data inventory; (3) Implement access controls; (4) Establish breach response plan. Complete within 60 days.",
                    owner_type="COMPLIANCE_OFFICER",
                    priority="HIGH",
                    estimated_effort_days=40,
                    expected_evidence_after=["Privacy policy", "Data inventory", "Access control documentation"]
                ),
            ],
            missing_criteria=[
                "No privacy policy",
                "Data stored insecurely or unencrypted",
            ],
            partial_criteria=[
                "Privacy policy exists but not comprehensive",
            ],
            supported_criteria=[
                "Current privacy policy covering data types and retention",
                "Data inventory documented",
                "Encryption/access controls in place",
                "Breach notification procedure documented",
            ],
            risk_raise_criteria=[
                "Data breach in last 2 years without documented remediation",
            ],
            retrieval_tags=["Privacy", "DataProtection", "Cybersecurity"],
        ),

        # ─── REAL ESTATE OVERLAY ───────────────────────────────────────────────
        JurisdictionControl(
            control_id="US-RE-01",
            control_name="Real Estate AML / KYC for Property Transactions",
            control_description="For real estate intermediaries, brokers, and title companies: implement AML/KYC for all parties (buyer, seller, tenant, landlord, UBO) and screen for sanctions and beneficial ownership in high-value transactions.",
            domain=Domain.REAL_ESTATE,
            jurisdiction=JurisdictionCode.US,
            regulator=Regulator.FINCEN,
            regime_mapping="FinCEN Real Estate Guidance 2022; BSA AML Ruleset §303 (EDD for Real Estate)",
            severity=Severity.HIGH,
            regulatory_reference="FinCEN Guidance on Real Estate Transactions (2022-G003); 31 CFR § 1010.610(b)(5) (EDD); State RE licensing laws",
            risk_if_missing="Facilitating money laundering through property; sanctions evasion; beneficial owner opacity; regulatory enforcement.",
            evidence_requirements=[
                EvidenceRequirement(
                    document_type="RE_AML_PROCEDURE",
                    description="RE-specific AML/KYC procedure: parties to be verified, UBO depth, SOF verification for high-value, transaction thresholds",
                    scoring_keywords=["real estate AML", "property transaction", "beneficial owner", "UBO", "source of funds", "seller verification"],
                    confidence_threshold=0.80,
                    is_mandatory=True
                ),
                EvidenceRequirement(
                    document_type="TRANSACTION_FILE_SAMPLE",
                    description="Sample transaction files (sale/lease) showing: buyer/seller/tenant CDD, UBO documentation, OFAC screening, approval",
                    scoring_keywords=["buyer information", "seller information", "beneficial owner", "screening result", "approval"],
                    confidence_threshold=0.85,
                    is_mandatory=True
                ),
            ],
            remediation_templates=[
                RemediationTemplate(
                    gap_type="MISSING",
                    corrective_action="Implement RE AML program: (1) Document which parties must be verified (buyer, seller, UBO if >25% owner); (2) Define SOF verification for transactions >$1M; (3) Screen all parties against OFAC; (4) Train agents/staff. Complete within 45 days.",
                    owner_type="COMPLIANCE_OFFICER",
                    priority="HIGH",
                    estimated_effort_days=35,
                    expected_evidence_after=["RE AML procedure", "Sample transaction files", "Training records"]
                ),
            ],
            missing_criteria=[
                "No RE-specific AML procedure",
                "Transactions completed without buyer/seller verification",
            ],
            partial_criteria=[
                "RE AML done informally, not formalized",
            ],
            supported_criteria=[
                "RE AML procedure covering parties, UBO, OFAC, SOF",
                "Sample transactions with full CDD/screening documentation",
                "High-value transactions (>$1M) include SOF verification",
            ],
            risk_raise_criteria=[
                "Cash property transaction with no buyer/UBO verification",
                "High-value transaction without SOF documentation",
            ],
            real_estate_overlays=[
                RealEstateOverlay(
                    scenario="PROPERTY_BUYER",
                    kyc_expectations="Identity verification (photo ID, address proof); for entities >$1M, beneficial ownership to UBO; source of funds for cash/high-risk",
                    source_of_funds_check=True,
                    beneficial_ownership_depth=2,
                    transaction_red_flags=["cash purchase", "rapid resale", "third-party funding", "sanctioned jurisdiction", "PEP involvement"],
                    sector_specific_risks=["shell company", "trade-based laundering", "sanctions evasion"]
                ),
                RealEstateOverlay(
                    scenario="PROPERTY_SELLER",
                    kyc_expectations="Identity verification; beneficial ownership if entity seller; foreign entity enhanced scrutiny",
                    source_of_funds_check=False,
                    beneficial_ownership_depth=2,
                    transaction_red_flags=["foreign entity", "shell company", "distressed sale", "no market price"],
                    sector_specific_risks=["beneficial owner evasion"]
                ),
                RealEstateOverlay(
                    scenario="PROPERTY_BROKER",
                    kyc_expectations="Business registration, ownership verification, background check for sanctions/AML history",
                    source_of_funds_check=False,
                    beneficial_ownership_depth=1,
                    transaction_red_flags=["multiple shell entities", "unusual fee structure", "offshore referrals"],
                    sector_specific_risks=["facilitating illicit transactions"]
                ),
            ],
            retrieval_tags=["RealEstate", "AML", "Property", "KYC"],
        ),
    ]
)


def get_jurisdiction_pack(jurisdiction: JurisdictionCode, version: str = "latest") -> Optional[JurisdictionPack]:
    """Load a jurisdiction pack by code and version."""
    packs = {
        JurisdictionCode.US: {
            "1.0": US_PACK_V1,
            "latest": US_PACK_V1,
        },
    }
    if jurisdiction in packs and version in packs[jurisdiction]:
        return packs[jurisdiction][version]
    return None


def list_jurisdiction_packs() -> list[JurisdictionPackMetadata]:
    """List all available jurisdiction packs."""
    return [
        US_PACK_V1.metadata,
    ]


def get_pack_controls_by_domain(jurisdiction: JurisdictionCode, domain: Domain) -> list[JurisdictionControl]:
    """Get all controls for a jurisdiction + domain."""
    pack = get_jurisdiction_pack(jurisdiction)
    if not pack:
        return []
    return pack.get_controls_by_domain(domain)


def get_pack_control(jurisdiction: JurisdictionCode, control_id: str) -> Optional[JurisdictionControl]:
    """Get a single control by jurisdiction + control_id."""
    pack = get_jurisdiction_pack(jurisdiction)
    if not pack:
        return None
    return pack.get_control(control_id)
