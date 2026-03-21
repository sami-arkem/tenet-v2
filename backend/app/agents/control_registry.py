"""
Gold Case Control Registry — Bible §11.
The authoritative set of compliance controls across all regimes.
Deterministic: this file is the single source of truth.
No model involvement in control definitions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Regime(str, Enum):
    AML = "AML"
    KYC = "KYC"
    SANCTIONS = "SANCTIONS"
    GDPR = "GDPR"
    FCA = "FCA"
    MIFID = "MIFID"
    PSD2 = "PSD2"
    DORA = "DORA"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Control:
    control_id: str                     # e.g. "AML-01"
    regime: Regime
    name: str
    description: str
    regulatory_reference: str           # e.g. "POCA 2002 s.330; MLR 2017 Reg 19"
    severity: Severity
    required_evidence_types: list[str]  # DocumentType values
    scoring_keywords: list[str]         # deterministic keywords for evidence scoring
    pass_threshold: float = 0.80        # Bible Rule 1: ≥ this → PASS
    partial_threshold: float = 0.50     # ≥ this → PARTIAL; below → FAIL
    jurisdictions: list[str] = field(default_factory=lambda: ["GB", "EU", "US", "GLOBAL"])
    gap_template: str = ""              # template for gap_description when not PASS
    risk_template: str = ""             # template for risk_description


# ─── AML Controls ─────────────────────────────────────────────────────────────

AML_CONTROLS: list[Control] = [
    Control(
        control_id="AML-01",
        regime=Regime.AML,
        name="AML Policy — Written and Board-Approved",
        description="The firm must maintain a written AML policy approved by the board of directors, covering all elements required by the Money Laundering Regulations 2017.",
        regulatory_reference="MLR 2017 Reg 19(1); JMLSG Part I §2.1",
        severity=Severity.CRITICAL,
        required_evidence_types=["AML_POLICY", "BOARD_MINUTES"],
        scoring_keywords=[
            "anti-money laundering policy", "aml policy", "board approved", "board approval",
            "money laundering regulations", "proceeds of crime", "suspicious activity report",
            "tipping off", "financial crime", "mlr 2017", "jmlsg",
        ],
        gap_template="AML policy document not found or lacks board approval evidence.",
        risk_template="Without a written board-approved AML policy, the firm is in breach of MLR 2017 Reg 19 and faces unlimited regulatory sanction.",
    ),
    Control(
        control_id="AML-02",
        regime=Regime.AML,
        name="MLRO Appointment — Nominated Officer",
        description="The firm must appoint a Money Laundering Reporting Officer (MLRO) who is a senior employee responsible for receiving and making SARs.",
        regulatory_reference="POCA 2002 s.331; MLR 2017 Reg 21",
        severity=Severity.CRITICAL,
        required_evidence_types=["AML_POLICY", "BOARD_MINUTES"],
        scoring_keywords=[
            "mlro", "money laundering reporting officer", "nominated officer",
            "senior responsible officer", "sar submission", "national crime agency",
            "nca", "suspicious activity", "disclosure officer",
        ],
        gap_template="MLRO appointment not evidenced. No named officer responsible for SAR submissions found.",
        risk_template="Failure to appoint an MLRO is a criminal offence under POCA 2002. The firm and senior management face personal liability.",
    ),
    Control(
        control_id="AML-03",
        regime=Regime.AML,
        name="Customer Due Diligence (CDD) — Standard Measures",
        description="The firm must apply standard CDD measures to all customers, including identity verification and beneficial ownership determination.",
        regulatory_reference="MLR 2017 Reg 27-28; FATF Recommendation 10",
        severity=Severity.CRITICAL,
        required_evidence_types=["KYC_PROCEDURE"],
        scoring_keywords=[
            "customer due diligence", "cdd", "identity verification", "id verification",
            "beneficial owner", "beneficial ownership", "ubo", "verification procedure",
            "documentary evidence", "customer identification", "fatf",
        ],
        gap_template="Standard CDD procedures not documented or lack identity verification process.",
        risk_template="Inadequate CDD enables criminals to use the firm for money laundering, exposing it to enforcement action and reputational damage.",
    ),
    Control(
        control_id="AML-04",
        regime=Regime.AML,
        name="Enhanced Due Diligence (EDD) — High Risk Customers",
        description="The firm must apply EDD to high-risk customers including PEPs, high-risk jurisdictions, and complex structures.",
        regulatory_reference="MLR 2017 Reg 33; JMLSG Part I §5",
        severity=Severity.HIGH,
        required_evidence_types=["KYC_PROCEDURE"],
        scoring_keywords=[
            "enhanced due diligence", "edd", "politically exposed person", "pep",
            "high risk", "high-risk jurisdiction", "complex structure",
            "source of funds", "source of wealth", "senior management approval",
            "enhanced monitoring",
        ],
        gap_template="EDD procedures not documented for high-risk customer categories.",
        risk_template="Without EDD for high-risk customers, the firm is exposed to higher money laundering risk and regulatory breach of MLR 2017 Reg 33.",
    ),
    Control(
        control_id="AML-05",
        regime=Regime.AML,
        name="Transaction Monitoring — Automated System",
        description="The firm must maintain a transaction monitoring system that detects unusual activity, with documented alert thresholds and investigation procedures.",
        regulatory_reference="MLR 2017 Reg 28(11); FCA SYSC 6.3.1",
        severity=Severity.CRITICAL,
        required_evidence_types=["TRANSACTION_MONITORING_POLICY"],
        scoring_keywords=[
            "transaction monitoring", "monitoring system", "alert threshold",
            "unusual transactions", "structuring", "velocity", "behavioural analytics",
            "ml model", "rule-based", "alert investigation", "case management",
            "l-sat", "actimize", "fircosoft", "oracle fccm",
        ],
        gap_template="Transaction monitoring system not documented or alert thresholds not defined.",
        risk_template="Absence of automated transaction monitoring is a critical gap enabling large-scale financial crime to go undetected.",
    ),
    Control(
        control_id="AML-06",
        regime=Regime.AML,
        name="Suspicious Activity Reporting — SAR Procedure",
        description="The firm must have a documented procedure for staff to report suspicions internally, and for the MLRO to submit SARs to the NCA.",
        regulatory_reference="POCA 2002 s.330-332; MLR 2017 Reg 21(3)",
        severity=Severity.HIGH,
        required_evidence_types=["AML_POLICY"],
        scoring_keywords=[
            "suspicious activity report", "sar", "national crime agency", "nca",
            "internal disclosure", "tipping off", "prejudicing investigation",
            "consent sar", "defence sar", "nominated officer",
        ],
        gap_template="SAR reporting procedure not documented.",
        risk_template="Without a SAR procedure, the firm and its staff risk committing criminal offences under POCA 2002.",
    ),
    Control(
        control_id="AML-07",
        regime=Regime.AML,
        name="AML Staff Training — Annual Requirement",
        description="All relevant staff must receive AML training at least annually, with records maintained.",
        regulatory_reference="MLR 2017 Reg 24; FCA TC 2.1",
        severity=Severity.HIGH,
        required_evidence_types=["TRAINING_RECORDS"],
        scoring_keywords=[
            "aml training", "anti-money laundering training", "training records",
            "training completion", "staff training", "annual training",
            "e-learning", "training certificate", "training log",
        ],
        gap_template="AML training records not provided or training not completed within 12 months.",
        risk_template="Untrained staff are unable to recognise money laundering indicators, creating direct exposure to facilitation of financial crime.",
    ),
    Control(
        control_id="AML-08",
        regime=Regime.AML,
        name="Risk Assessment — Firm-Wide ML/TF Risk Assessment",
        description="The firm must conduct and document a firm-wide money laundering and terrorist financing risk assessment, reviewed annually.",
        regulatory_reference="MLR 2017 Reg 18; FATF Recommendation 1",
        severity=Severity.HIGH,
        required_evidence_types=["RISK_ASSESSMENT"],
        scoring_keywords=[
            "risk assessment", "money laundering risk", "terrorist financing risk",
            "ml/tf risk", "inherent risk", "residual risk", "risk appetite",
            "business risk assessment", "national risk assessment",
            "customer risk", "product risk", "geographic risk",
        ],
        gap_template="Firm-wide ML/TF risk assessment not provided or not current (within 12 months).",
        risk_template="Without a risk assessment, the firm cannot proportionately allocate compliance resources, creating systemic risk exposure.",
    ),
    Control(
        control_id="AML-09",
        regime=Regime.AML,
        name="Sanctions Screening — Real-Time Customer and Payment Screening",
        description="The firm must screen all customers and payments against applicable sanctions lists (OFAC, UN, EU, UK HMT) in real-time.",
        regulatory_reference="SAMLA 2018; OFAC 31 CFR Part 500; EU Reg 2580/2001",
        severity=Severity.CRITICAL,
        required_evidence_types=["SANCTIONS_POLICY"],
        scoring_keywords=[
            "sanctions screening", "ofac", "un security council", "hm treasury",
            "consolidated list", "sdn list", "eu sanctions", "real-time screening",
            "payment screening", "name screening", "sanctions hits", "false positive",
        ],
        gap_template="Sanctions screening programme not documented or no evidence of real-time payment screening.",
        risk_template="Failure to screen against sanctions lists risks facilitating transactions with sanctioned entities, resulting in unlimited civil and criminal penalties.",
    ),
    Control(
        control_id="AML-10",
        regime=Regime.AML,
        name="Record Keeping — 5-Year Retention",
        description="The firm must retain CDD records, transaction records, and internal reports for a minimum of 5 years.",
        regulatory_reference="MLR 2017 Reg 40; POCA 2002 s.333B",
        severity=Severity.HIGH,
        required_evidence_types=["DATA_RETENTION_POLICY"],
        scoring_keywords=[
            "record keeping", "data retention", "5 year", "five year", "retention period",
            "cdd records", "transaction records", "retention schedule", "data disposal",
        ],
        gap_template="Data retention policy not provided or retention period not clearly 5+ years for AML records.",
        risk_template="Insufficient record keeping prevents regulators from conducting investigations and exposes the firm to obstruction charges.",
    ),
]

# ─── GDPR Controls ────────────────────────────────────────────────────────────

GDPR_CONTROLS: list[Control] = [
    Control(
        control_id="GDPR-01",
        regime=Regime.GDPR,
        name="Privacy Notice — Compliant and Published",
        description="The firm must publish a clear, accurate privacy notice covering all required GDPR Article 13/14 elements.",
        regulatory_reference="GDPR Art 13-14; UK GDPR Art 13-14",
        severity=Severity.HIGH,
        required_evidence_types=["GDPR_PRIVACY_NOTICE"],
        scoring_keywords=[
            "privacy notice", "privacy policy", "data controller", "lawful basis",
            "legitimate interest", "consent", "right to access", "right to erasure",
            "right to rectification", "data subject rights", "dpo",
            "data protection officer", "supervisory authority", "ico",
        ],
        gap_template="Privacy notice not provided or lacks required GDPR elements.",
        risk_template="Non-compliant privacy notice exposes the firm to ICO enforcement and fines up to 4% of global turnover.",
    ),
    Control(
        control_id="GDPR-02",
        regime=Regime.GDPR,
        name="Data Retention Policy — Defined Schedules",
        description="The firm must have a documented data retention policy with specific schedules for each data category.",
        regulatory_reference="GDPR Art 5(1)(e); UK GDPR Art 5(1)(e)",
        severity=Severity.HIGH,
        required_evidence_types=["DATA_RETENTION_POLICY"],
        scoring_keywords=[
            "data retention", "retention schedule", "retention period", "data deletion",
            "data disposal", "data lifecycle", "purge schedule", "storage limitation",
            "retention policy", "personal data", "data category",
        ],
        gap_template="Data retention policy not provided or lacks schedules for personal data categories.",
        risk_template="Without defined retention schedules, the firm risks retaining personal data longer than necessary, breaching GDPR storage limitation principle.",
    ),
    Control(
        control_id="GDPR-03",
        regime=Regime.GDPR,
        name="Data Subject Rights — Operational Procedures",
        description="The firm must have documented procedures for handling data subject access requests (DSARs), erasure requests, and other rights within statutory timescales.",
        regulatory_reference="GDPR Art 12-22; UK GDPR Art 12-22",
        severity=Severity.MEDIUM,
        required_evidence_types=["GDPR_PRIVACY_NOTICE"],
        scoring_keywords=[
            "data subject access request", "dsar", "right to erasure", "right to be forgotten",
            "right to rectification", "right to portability", "right to object",
            "automated decision", "30 days", "one month", "data subject request",
        ],
        gap_template="DSAR handling procedure not documented.",
        risk_template="Failure to respond to DSARs within 30 days is a regulatory breach that can result in ICO enforcement action.",
    ),
    Control(
        control_id="GDPR-04",
        regime=Regime.GDPR,
        name="Data Protection Officer — Appointed Where Required",
        description="The firm must appoint a DPO where required and document their role and contact details.",
        regulatory_reference="GDPR Art 37-39; UK GDPR Art 37-39",
        severity=Severity.MEDIUM,
        required_evidence_types=["GDPR_PRIVACY_NOTICE"],
        scoring_keywords=[
            "data protection officer", "dpo", "appointed", "dpo contact",
            "dpo responsibilities", "art 37", "article 37",
            "public authority", "large scale processing",
        ],
        gap_template="DPO appointment not evidenced where required.",
        risk_template="Failure to appoint a DPO where required is a direct GDPR breach.",
    ),
    Control(
        control_id="GDPR-05",
        regime=Regime.GDPR,
        name="Data Breach Response — 72-Hour Notification Procedure",
        description="The firm must have a documented data breach response procedure including 72-hour notification to the supervisory authority.",
        regulatory_reference="GDPR Art 33-34; UK GDPR Art 33-34",
        severity=Severity.HIGH,
        required_evidence_types=["GDPR_PRIVACY_NOTICE", "RISK_ASSESSMENT"],
        scoring_keywords=[
            "data breach", "personal data breach", "72 hours", "notification",
            "supervisory authority", "ico", "breach response", "incident response",
            "breach register", "containment", "investigation",
        ],
        gap_template="Data breach response procedure not documented or 72-hour notification process not defined.",
        risk_template="Without a breach procedure, the firm risks failing to notify within 72 hours, resulting in fines up to 4% of global turnover.",
    ),
]

# ─── FCA Controls ─────────────────────────────────────────────────────────────

FCA_CONTROLS: list[Control] = [
    Control(
        control_id="FCA-01",
        regime=Regime.FCA,
        name="Systems and Controls — SYSC Framework",
        description="The firm must have adequate systems and controls as required by FCA SYSC, including governance, risk management, and compliance oversight.",
        regulatory_reference="FCA SYSC 4.1, 6.1; PS21/3",
        severity=Severity.CRITICAL,
        required_evidence_types=["BOARD_MINUTES", "RISK_ASSESSMENT"],
        scoring_keywords=[
            "systems and controls", "sysc", "governance framework", "risk management",
            "compliance oversight", "senior management arrangements", "smcr",
            "senior managers", "certified persons", "conduct rules",
        ],
        gap_template="SYSC-compliant systems and controls framework not evidenced.",
        risk_template="Inadequate systems and controls is a breach of FCA's threshold conditions and may result in licence withdrawal.",
    ),
    Control(
        control_id="FCA-02",
        regime=Regime.FCA,
        name="SMCR — Senior Managers Regime Compliance",
        description="The firm must comply with the Senior Managers and Certification Regime, with all required functions allocated and documented.",
        regulatory_reference="FCA SUP 10C; FSMA 2000 s.59",
        severity=Severity.HIGH,
        required_evidence_types=["BOARD_MINUTES"],
        scoring_keywords=[
            "senior managers regime", "smcr", "senior manager", "certification regime",
            "prescribed responsibilities", "statement of responsibilities",
            "conduct rules", "individual accountability", "fem",
            "fit and proper", "smd", "cf", "controlled function",
        ],
        gap_template="SMCR compliance not evidenced — prescribed responsibilities not allocated.",
        risk_template="SMCR non-compliance exposes senior managers to personal regulatory action including prohibition.",
    ),
    Control(
        control_id="FCA-03",
        regime=Regime.FCA,
        name="Customer Outcomes — Consumer Duty",
        description="The firm must demonstrate compliance with FCA Consumer Duty, evidencing good customer outcomes across all four outcome areas.",
        regulatory_reference="FCA PRIN 2A; PS22/9 (Consumer Duty)",
        severity=Severity.HIGH,
        required_evidence_types=["RISK_ASSESSMENT", "BOARD_MINUTES"],
        scoring_keywords=[
            "consumer duty", "customer outcomes", "good outcomes", "products and services",
            "price and value", "consumer understanding", "consumer support",
            "vulnerable customers", "fair value", "fca ps22/9",
        ],
        gap_template="Consumer Duty compliance not evidenced — outcome monitoring not documented.",
        risk_template="Consumer Duty breaches risk regulatory action, mandatory redress, and reputational damage.",
    ),
]

# ─── Sanctions Controls ───────────────────────────────────────────────────────

SANCTIONS_CONTROLS: list[Control] = [
    Control(
        control_id="SAN-01",
        regime=Regime.SANCTIONS,
        name="Sanctions Programme — Comprehensive Written Policy",
        description="The firm must maintain a written sanctions compliance programme covering all applicable sanctions regimes.",
        regulatory_reference="OFAC SDN List requirements; SAMLA 2018; EU Reg 2580/2001",
        severity=Severity.CRITICAL,
        required_evidence_types=["SANCTIONS_POLICY"],
        scoring_keywords=[
            "sanctions policy", "sanctions programme", "sanctions compliance",
            "ofac", "un security council", "hm treasury", "eu sanctions",
            "embargo", "restricted party", "comprehensive sanctions",
        ],
        gap_template="Sanctions compliance programme not documented.",
        risk_template="Without a sanctions programme, the firm risks violating sanctions laws with penalties including unlimited fines and criminal prosecution.",
    ),
    Control(
        control_id="SAN-02",
        regime=Regime.SANCTIONS,
        name="Sanctions Screening — Automated Real-Time System",
        description="The firm must screen customers and transactions in real-time against all applicable consolidated sanctions lists.",
        regulatory_reference="OFAC 31 CFR Part 501; FCA SYSC 6.3",
        severity=Severity.CRITICAL,
        required_evidence_types=["SANCTIONS_POLICY", "TRANSACTION_MONITORING_POLICY"],
        scoring_keywords=[
            "real-time screening", "automated screening", "sanctions list",
            "consolidated list", "sdn", "pep and sanctions", "screening system",
            "name matching", "fuzzy matching", "false positive management",
            "hit investigation", "screening frequency",
        ],
        gap_template="Real-time sanctions screening system not evidenced.",
        risk_template="Manual or batch sanctions screening leaves the firm exposed to processing sanctioned transactions, a strict liability offence.",
    ),
]

# ─── Registry ─────────────────────────────────────────────────────────────────

_ALL_CONTROLS: list[Control] = AML_CONTROLS + GDPR_CONTROLS + FCA_CONTROLS + SANCTIONS_CONTROLS

_CONTROL_INDEX: dict[str, Control] = {c.control_id: c for c in _ALL_CONTROLS}

_REGIME_INDEX: dict[Regime, list[Control]] = {}
for _ctrl in _ALL_CONTROLS:
    _REGIME_INDEX.setdefault(_ctrl.regime, []).append(_ctrl)


def get_controls_for_regimes(regime_scope: list[str]) -> list[Control]:
    """Return all controls applicable to the given regime scope."""
    result = []
    seen: set[str] = set()
    for regime_str in regime_scope:
        try:
            regime = Regime(regime_str.upper())
        except ValueError:
            continue
        for ctrl in _REGIME_INDEX.get(regime, []):
            if ctrl.control_id not in seen:
                result.append(ctrl)
                seen.add(ctrl.control_id)
    return result


def get_control(control_id: str) -> Control | None:
    return _CONTROL_INDEX.get(control_id)


def list_all_controls() -> list[Control]:
    return list(_ALL_CONTROLS)


def list_regimes() -> list[str]:
    return [r.value for r in Regime]
