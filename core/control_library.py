from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_string_list(values: Any, field_name: str) -> list[str]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{field_name} must be a non-empty list[str]")
    out: list[str] = []
    for idx, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name}[{idx}] must be a non-empty string")
        out.append(value.strip())
    return out


@dataclass(frozen=True)
class ApplicabilityRule:
    domains: list[str]
    jurisdictions: list[str]
    framework_ids: list[str]
    entity_types: list[str]
    product_tags: list[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "domains", _require_string_list(self.domains, "domains"))
        object.__setattr__(self, "jurisdictions", _require_string_list(self.jurisdictions, "jurisdictions"))
        object.__setattr__(self, "framework_ids", _require_string_list(self.framework_ids, "framework_ids"))
        object.__setattr__(self, "entity_types", _require_string_list(self.entity_types, "entity_types"))
        object.__setattr__(self, "product_tags", _require_string_list(self.product_tags, "product_tags"))


@dataclass(frozen=True)
class LibraryControl:
    control_id: str
    regime_id: str
    framework_id: str
    domain: str
    title: str
    description: str
    test_procedure: str
    required_evidence_types: list[str]
    severity_if_missing: str
    applicability: ApplicabilityRule

    def __post_init__(self) -> None:
        object.__setattr__(self, "control_id", _require_non_empty_str(self.control_id, "control_id"))
        object.__setattr__(self, "regime_id", _require_non_empty_str(self.regime_id, "regime_id"))
        object.__setattr__(self, "framework_id", _require_non_empty_str(self.framework_id, "framework_id"))
        object.__setattr__(self, "domain", _require_non_empty_str(self.domain, "domain"))
        object.__setattr__(self, "title", _require_non_empty_str(self.title, "title"))
        object.__setattr__(self, "description", _require_non_empty_str(self.description, "description"))
        object.__setattr__(self, "test_procedure", _require_non_empty_str(self.test_procedure, "test_procedure"))
        object.__setattr__(self, "required_evidence_types", _require_string_list(self.required_evidence_types, "required_evidence_types"))
        object.__setattr__(self, "severity_if_missing", _require_non_empty_str(self.severity_if_missing, "severity_if_missing"))
        if not isinstance(self.applicability, ApplicabilityRule):
            raise ValueError("applicability must be ApplicabilityRule")

    def to_control_payload(self) -> dict[str, Any]:
        return {
            "control_id": self.control_id,
            "regime_id": self.regime_id,
            "title": self.title,
            "description": self.description,
            "test_procedure": self.test_procedure,
            "required_evidence_types": self.required_evidence_types,
            "severity_if_missing": self.severity_if_missing,
        }


def build_default_control_library() -> list[LibraryControl]:
    return [
        LibraryControl(
            control_id="AML.MONITORING.001",
            regime_id="UK_MLR.001",
            framework_id="UK_MLR",
            domain="aml",
            title="Transaction monitoring policy",
            description="A documented transaction monitoring policy must exist.",
            test_procedure="Verify policy coverage and monitoring evidence.",
            required_evidence_types=["policy_document", "monitoring_report"],
            severity_if_missing="HIGH",
            applicability=ApplicabilityRule(
                domains=["aml"],
                jurisdictions=["uk", "eu"],
                framework_ids=["UK_MLR", "EU_AMLD6"],
                entity_types=["regulated_entity", "fintech"],
                product_tags=["payments", "wallets"],
            ),
        ),
        LibraryControl(
            control_id="AML.KYC.002",
            regime_id="UK_MLR.002",
            framework_id="UK_MLR",
            domain="kyc",
            title="CDD review evidence",
            description="Customer due diligence review evidence must exist.",
            test_procedure="Verify periodic review logs and sample evidence.",
            required_evidence_types=["periodic_review_log", "cdd_policy"],
            severity_if_missing="HIGH",
            applicability=ApplicabilityRule(
                domains=["aml", "kyc"],
                jurisdictions=["uk", "eu"],
                framework_ids=["UK_MLR", "EU_AMLD6"],
                entity_types=["regulated_entity", "fintech"],
                product_tags=["payments", "wallets", "accounts"],
            ),
        ),
        LibraryControl(
            control_id="SANCTIONS.SCREENING.001",
            regime_id="EU_SANCTIONS.001",
            framework_id="EU_SANCTIONS",
            domain="sanctions",
            title="Sanctions screening evidence",
            description="Sanctions screening must exist for relevant customers and transactions.",
            test_procedure="Verify sanctions screening procedures and alert evidence.",
            required_evidence_types=["screening_policy", "screening_alert_log"],
            severity_if_missing="CRITICAL",
            applicability=ApplicabilityRule(
                domains=["sanctions", "aml"],
                jurisdictions=["eu", "uk", "us"],
                framework_ids=["EU_SANCTIONS", "OFAC", "UK_HMT"],
                entity_types=["regulated_entity", "fintech"],
                product_tags=["payments", "wallets", "cross_border"],
            ),
        ),
        LibraryControl(
            control_id="GOV.RISK.001",
            regime_id="INT_GOV.001",
            framework_id="INT_GOV",
            domain="governance",
            title="Compliance governance ownership",
            description="Named ownership and governance review must exist.",
            test_procedure="Verify governance charter and ownership evidence.",
            required_evidence_types=["governance_charter", "owner_matrix"],
            severity_if_missing="MEDIUM",
            applicability=ApplicabilityRule(
                domains=["governance", "aml", "kyc", "sanctions"],
                jurisdictions=["global", "uk", "eu", "us"],
                framework_ids=["INT_GOV", "UK_MLR", "EU_AMLD6", "OFAC"],
                entity_types=["regulated_entity", "fintech", "vendor"],
                product_tags=["payments", "wallets", "accounts", "vendor_platform"],
            ),
        ),
        LibraryControl(
            control_id="VENDOR.RISK.001",
            regime_id="TPRM.001",
            framework_id="TPRM",
            domain="vendor_risk",
            title="Critical vendor due diligence",
            description="Critical vendors must undergo due diligence and risk review.",
            test_procedure="Verify vendor inventory and due diligence evidence.",
            required_evidence_types=["vendor_inventory", "vendor_due_diligence"],
            severity_if_missing="HIGH",
            applicability=ApplicabilityRule(
                domains=["vendor_risk", "third_party_risk", "governance"],
                jurisdictions=["global", "uk", "eu", "us"],
                framework_ids=["TPRM", "INT_GOV"],
                entity_types=["regulated_entity", "fintech", "vendor"],
                product_tags=["payments", "wallets", "vendor_platform"],
            ),
        ),
    ]
