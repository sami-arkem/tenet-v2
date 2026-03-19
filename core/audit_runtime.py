from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_non_empty_str(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_string_list(values: list[str], field_name: str) -> list[str]:
    if not isinstance(values, list):
        raise ValueError(f"{field_name} must be a list[str]")
    out: list[str] = []
    for idx, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name}[{idx}] must be a non-empty string")
        out.append(value.strip())
    return out


class EvidenceVerdict(str, Enum):
    SATISFIED = "SATISFIED"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    FAILING = "FAILING"


class FindingSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FindingStatus(str, Enum):
    OPEN = "OPEN"
    IN_REMEDIATION = "IN_REMEDIATION"
    CLOSED = "CLOSED"


class OverallPosture(str, Enum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"


class DeploymentDecision(str, Enum):
    APPROVED = "APPROVED"
    CONDITIONALLY_APPROVED = "CONDITIONALLY_APPROVED"
    BLOCKED = "BLOCKED"


class AuditRunStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CompanyProfile:
    company_name: str
    industry: str
    primary_jurisdiction: str
    additional_jurisdictions: list[str]
    products: list[str]
    entities: list[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "company_name", _require_non_empty_str(self.company_name, "company_name"))
        object.__setattr__(self, "industry", _require_non_empty_str(self.industry, "industry"))
        object.__setattr__(self, "primary_jurisdiction", _require_non_empty_str(self.primary_jurisdiction, "primary_jurisdiction"))
        object.__setattr__(self, "additional_jurisdictions", _require_string_list(self.additional_jurisdictions, "additional_jurisdictions"))
        object.__setattr__(self, "products", _require_string_list(self.products, "products"))
        object.__setattr__(self, "entities", _require_string_list(self.entities, "entities"))


@dataclass(frozen=True)
class AuditScope:
    audit_id: str
    audit_type: str
    framework_ids: list[str]
    domain: str
    domains: list[str]
    jurisdictions: list[str]
    in_scope_entities: list[str]
    in_scope_products: list[str]
    evaluation_date: str
    historical_context_is_non_authoritative: bool = True
    deterministic_current_audit_truth_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "audit_id", _require_non_empty_str(self.audit_id, "audit_id"))
        object.__setattr__(self, "audit_type", _require_non_empty_str(self.audit_type, "audit_type"))
        object.__setattr__(self, "framework_ids", _require_string_list(self.framework_ids, "framework_ids"))
        object.__setattr__(self, "domain", _require_non_empty_str(self.domain, "domain"))
        object.__setattr__(self, "domains", _require_string_list(self.domains, "domains"))
        object.__setattr__(self, "jurisdictions", _require_string_list(self.jurisdictions, "jurisdictions"))
        object.__setattr__(self, "in_scope_entities", _require_string_list(self.in_scope_entities, "in_scope_entities"))
        object.__setattr__(self, "in_scope_products", _require_string_list(self.in_scope_products, "in_scope_products"))
        object.__setattr__(self, "evaluation_date", _require_non_empty_str(self.evaluation_date, "evaluation_date"))
        if self.historical_context_is_non_authoritative is not True:
            raise ValueError("historical_context_is_non_authoritative must be true")
        if self.deterministic_current_audit_truth_only is not True:
            raise ValueError("deterministic_current_audit_truth_only must be true")


@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str
    title: str
    source_type: str
    file_path: str
    citation: str
    content_hash: str | None = None
    collected_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", _require_non_empty_str(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "title", _require_non_empty_str(self.title, "title"))
        object.__setattr__(self, "source_type", _require_non_empty_str(self.source_type, "source_type"))
        object.__setattr__(self, "file_path", _require_non_empty_str(self.file_path, "file_path"))
        object.__setattr__(self, "citation", _require_non_empty_str(self.citation, "citation"))


@dataclass(frozen=True)
class ControlDefinition:
    control_id: str
    regime_id: str
    title: str
    description: str
    test_procedure: str
    required_evidence_types: list[str]
    severity_if_missing: FindingSeverity

    def __post_init__(self) -> None:
        object.__setattr__(self, "control_id", _require_non_empty_str(self.control_id, "control_id"))
        object.__setattr__(self, "regime_id", _require_non_empty_str(self.regime_id, "regime_id"))
        object.__setattr__(self, "title", _require_non_empty_str(self.title, "title"))
        object.__setattr__(self, "description", _require_non_empty_str(self.description, "description"))
        object.__setattr__(self, "test_procedure", _require_non_empty_str(self.test_procedure, "test_procedure"))
        object.__setattr__(self, "required_evidence_types", _require_string_list(self.required_evidence_types, "required_evidence_types"))


@dataclass(frozen=True)
class ControlInput:
    control: ControlDefinition
    provided_evidence: list[EvidenceReference]
    declared_control_present: bool
    declared_operating_effective: bool | None
    notes: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.control, ControlDefinition):
            raise ValueError("control must be ControlDefinition")
        if not isinstance(self.provided_evidence, list):
            raise ValueError("provided_evidence must be list[EvidenceReference]")
        for idx, evidence in enumerate(self.provided_evidence):
            if not isinstance(evidence, EvidenceReference):
                raise ValueError(f"provided_evidence[{idx}] must be EvidenceReference")
        if self.declared_operating_effective is not None and not isinstance(self.declared_operating_effective, bool):
            raise ValueError("declared_operating_effective must be bool | None")
        if not isinstance(self.notes, str):
            raise ValueError("notes must be str")


@dataclass(frozen=True)
class Finding:
    finding_id: str
    control_id: str
    regime_id: str
    title: str
    description: str
    severity: FindingSeverity
    status: FindingStatus
    verdict: EvidenceVerdict
    missing_evidence_types: list[str]
    evidence_refs: list[EvidenceReference]
    remediation_actions: list[str]
    rationale: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "finding_id", _require_non_empty_str(self.finding_id, "finding_id"))
        object.__setattr__(self, "control_id", _require_non_empty_str(self.control_id, "control_id"))
        object.__setattr__(self, "regime_id", _require_non_empty_str(self.regime_id, "regime_id"))
        object.__setattr__(self, "title", _require_non_empty_str(self.title, "title"))
        object.__setattr__(self, "description", _require_non_empty_str(self.description, "description"))
        object.__setattr__(self, "missing_evidence_types", _require_string_list(self.missing_evidence_types, "missing_evidence_types"))
        object.__setattr__(self, "remediation_actions", _require_string_list(self.remediation_actions, "remediation_actions"))
        object.__setattr__(self, "rationale", _require_non_empty_str(self.rationale, "rationale"))
        if not isinstance(self.evidence_refs, list):
            raise ValueError("evidence_refs must be list[EvidenceReference]")
        for idx, evidence in enumerate(self.evidence_refs):
            if not isinstance(evidence, EvidenceReference):
                raise ValueError(f"evidence_refs[{idx}] must be EvidenceReference")


@dataclass(frozen=True)
class ControlEvaluation:
    control_id: str
    regime_id: str
    verdict: EvidenceVerdict
    evidence_coverage_ratio: float
    evidence_refs: list[EvidenceReference]
    findings: list[Finding]
    rationale: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "control_id", _require_non_empty_str(self.control_id, "control_id"))
        object.__setattr__(self, "regime_id", _require_non_empty_str(self.regime_id, "regime_id"))
        if not isinstance(self.evidence_coverage_ratio, (int, float)):
            raise ValueError("evidence_coverage_ratio must be numeric")
        if self.evidence_coverage_ratio < 0.0 or self.evidence_coverage_ratio > 1.0:
            raise ValueError("evidence_coverage_ratio must be between 0 and 1")
        if not isinstance(self.evidence_refs, list):
            raise ValueError("evidence_refs must be list[EvidenceReference]")
        if not isinstance(self.findings, list):
            raise ValueError("findings must be list[Finding]")
        for idx, evidence in enumerate(self.evidence_refs):
            if not isinstance(evidence, EvidenceReference):
                raise ValueError(f"evidence_refs[{idx}] must be EvidenceReference")
        for idx, finding in enumerate(self.findings):
            if not isinstance(finding, Finding):
                raise ValueError(f"findings[{idx}] must be Finding")
        object.__setattr__(self, "rationale", _require_non_empty_str(self.rationale, "rationale"))


@dataclass(frozen=True)
class RemediationItem:
    remediation_id: str
    finding_id: str
    title: str
    owner: str
    due_date: str | None
    status: FindingStatus
    action_required: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "remediation_id", _require_non_empty_str(self.remediation_id, "remediation_id"))
        object.__setattr__(self, "finding_id", _require_non_empty_str(self.finding_id, "finding_id"))
        object.__setattr__(self, "title", _require_non_empty_str(self.title, "title"))
        object.__setattr__(self, "owner", _require_non_empty_str(self.owner, "owner"))
        object.__setattr__(self, "action_required", _require_non_empty_str(self.action_required, "action_required"))


@dataclass(frozen=True)
class AuditSummary:
    overall_posture: OverallPosture
    deployment_decision: DeploymentDecision
    control_count: int
    passed_controls: int
    partial_controls: int
    failed_controls: int
    missing_evidence_controls: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    summary_text: str

    def __post_init__(self) -> None:
        for field_name in (
            "control_count",
            "passed_controls",
            "partial_controls",
            "failed_controls",
            "missing_evidence_controls",
            "critical_findings",
            "high_findings",
            "medium_findings",
            "low_findings",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be non-negative int")
        object.__setattr__(self, "summary_text", _require_non_empty_str(self.summary_text, "summary_text"))


@dataclass(frozen=True)
class DeterministicAuditResult:
    run_id: str
    status: AuditRunStatus
    created_at: str
    completed_at: str
    company_profile: CompanyProfile
    scope: AuditScope
    control_evaluations: list[ControlEvaluation]
    findings: list[Finding]
    remediation_items: list[RemediationItem]
    summary: AuditSummary
    prior_historical_context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _require_non_empty_str(self.run_id, "run_id"))
        object.__setattr__(self, "created_at", _require_non_empty_str(self.created_at, "created_at"))
        object.__setattr__(self, "completed_at", _require_non_empty_str(self.completed_at, "completed_at"))
        if not isinstance(self.company_profile, CompanyProfile):
            raise ValueError("company_profile must be CompanyProfile")
        if not isinstance(self.scope, AuditScope):
            raise ValueError("scope must be AuditScope")
        if not isinstance(self.summary, AuditSummary):
            raise ValueError("summary must be AuditSummary")
        if not isinstance(self.control_evaluations, list):
            raise ValueError("control_evaluations must be list[ControlEvaluation]")
        if not isinstance(self.findings, list):
            raise ValueError("findings must be list[Finding]")
        if not isinstance(self.remediation_items, list):
            raise ValueError("remediation_items must be list[RemediationItem]")
        for idx, value in enumerate(self.control_evaluations):
            if not isinstance(value, ControlEvaluation):
                raise ValueError(f"control_evaluations[{idx}] must be ControlEvaluation")
        for idx, value in enumerate(self.findings):
            if not isinstance(value, Finding):
                raise ValueError(f"findings[{idx}] must be Finding")
        for idx, value in enumerate(self.remediation_items):
            if not isinstance(value, RemediationItem):
                raise ValueError(f"remediation_items[{idx}] must be RemediationItem")
        if self.scope.historical_context_is_non_authoritative is not True:
            raise ValueError("scope must preserve historical_context_is_non_authoritative=true")
        if self.scope.deterministic_current_audit_truth_only is not True:
            raise ValueError("scope must preserve deterministic_current_audit_truth_only=true")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_control(control_input: ControlInput) -> ControlEvaluation:
    required = set(control_input.control.required_evidence_types)
    provided = {evidence.source_type for evidence in control_input.provided_evidence}
    matched = sorted(required.intersection(provided))
    missing = sorted(required.difference(provided))

    if not control_input.declared_control_present:
        verdict = EvidenceVerdict.FAILING
        rationale = "Declared control absent."
    elif missing and not matched:
        verdict = EvidenceVerdict.MISSING
        rationale = "No required evidence types were satisfied."
    elif missing:
        verdict = EvidenceVerdict.PARTIAL
        rationale = "Control present but evidence coverage is incomplete."
    elif control_input.declared_operating_effective is False:
        verdict = EvidenceVerdict.FAILING
        rationale = "Control present but declared not operating effectively."
    else:
        verdict = EvidenceVerdict.SATISFIED
        rationale = "Required evidence types are covered and control is declared effective."

    findings: list[Finding] = []
    if verdict != EvidenceVerdict.SATISFIED:
        remediation_actions: list[str] = []
        if not control_input.declared_control_present:
            remediation_actions.append("Implement the missing control and document ownership.")
        if missing:
            remediation_actions.append(f"Provide evidence covering missing evidence types: {', '.join(missing)}.")
        if control_input.declared_operating_effective is False:
            remediation_actions.append("Remediate operating effectiveness failure and retest.")

        findings.append(
            Finding(
                finding_id=f"{control_input.control.control_id}::finding",
                control_id=control_input.control.control_id,
                regime_id=control_input.control.regime_id,
                title=f"Gap in {control_input.control.title}",
                description=(
                    f"Deterministic evaluation found verdict={verdict.value} for control "
                    f"{control_input.control.control_id}."
                ),
                severity=control_input.control.severity_if_missing,
                status=FindingStatus.OPEN,
                verdict=verdict,
                missing_evidence_types=missing,
                evidence_refs=control_input.provided_evidence,
                remediation_actions=remediation_actions or ["Investigate control deficiency and provide evidence."],
                rationale=rationale,
            )
        )

    coverage_ratio = 1.0 if not required else round(len(matched) / len(required), 4)

    return ControlEvaluation(
        control_id=control_input.control.control_id,
        regime_id=control_input.control.regime_id,
        verdict=verdict,
        evidence_coverage_ratio=coverage_ratio,
        evidence_refs=control_input.provided_evidence,
        findings=findings,
        rationale=rationale,
    )


def summarize_audit(control_evaluations: list[ControlEvaluation]) -> AuditSummary:
    if not control_evaluations:
        raise ValueError("control_evaluations must be non-empty")

    passed = sum(1 for row in control_evaluations if row.verdict == EvidenceVerdict.SATISFIED)
    partial = sum(1 for row in control_evaluations if row.verdict == EvidenceVerdict.PARTIAL)
    failed = sum(1 for row in control_evaluations if row.verdict == EvidenceVerdict.FAILING)
    missing = sum(1 for row in control_evaluations if row.verdict == EvidenceVerdict.MISSING)

    findings = [finding for row in control_evaluations for finding in row.findings]
    critical = sum(1 for row in findings if row.severity == FindingSeverity.CRITICAL)
    high = sum(1 for row in findings if row.severity == FindingSeverity.HIGH)
    medium = sum(1 for row in findings if row.severity == FindingSeverity.MEDIUM)
    low = sum(1 for row in findings if row.severity == FindingSeverity.LOW)

    if critical > 0 or failed > 0:
        overall_posture = OverallPosture.RED
        deployment_decision = DeploymentDecision.BLOCKED
    elif high > 0 or partial > 0 or missing > 0:
        overall_posture = OverallPosture.AMBER
        deployment_decision = DeploymentDecision.CONDITIONALLY_APPROVED
    else:
        overall_posture = OverallPosture.GREEN
        deployment_decision = DeploymentDecision.APPROVED

    summary_text = (
        f"Deterministic audit completed with posture={overall_posture.value}, "
        f"decision={deployment_decision.value}, "
        f"controls={len(control_evaluations)}, "
        f"passed={passed}, partial={partial}, failed={failed}, missing_evidence={missing}."
    )

    return AuditSummary(
        overall_posture=overall_posture,
        deployment_decision=deployment_decision,
        control_count=len(control_evaluations),
        passed_controls=passed,
        partial_controls=partial,
        failed_controls=failed,
        missing_evidence_controls=missing,
        critical_findings=critical,
        high_findings=high,
        medium_findings=medium,
        low_findings=low,
        summary_text=summary_text,
    )


def build_remediation_items(findings: list[Finding], default_owner: str) -> list[RemediationItem]:
    owner = _require_non_empty_str(default_owner, "default_owner")
    items: list[RemediationItem] = []
    for idx, finding in enumerate(findings, start=1):
        items.append(
            RemediationItem(
                remediation_id=f"remediation::{idx:04d}",
                finding_id=finding.finding_id,
                title=f"Remediate {finding.control_id}",
                owner=owner,
                due_date=None,
                status=FindingStatus.OPEN,
                action_required=" ".join(finding.remediation_actions),
            )
        )
    return items


def run_deterministic_audit(
    *,
    run_id: str,
    company_profile: CompanyProfile,
    scope: AuditScope,
    control_inputs: list[ControlInput],
    default_remediation_owner: str,
    prior_historical_context: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> DeterministicAuditResult:
    _require_non_empty_str(run_id, "run_id")
    if not isinstance(control_inputs, list) or not control_inputs:
        raise ValueError("control_inputs must be non-empty list[ControlInput]")
    for idx, row in enumerate(control_inputs):
        if not isinstance(row, ControlInput):
            raise ValueError(f"control_inputs[{idx}] must be ControlInput")

    created_at = utc_now_iso()
    evaluations = [evaluate_control(row) for row in control_inputs]
    findings = [finding for row in evaluations for finding in row.findings]
    summary = summarize_audit(evaluations)
    remediation_items = build_remediation_items(findings, default_remediation_owner)
    completed_at = utc_now_iso()

    return DeterministicAuditResult(
        run_id=run_id,
        status=AuditRunStatus.COMPLETED,
        created_at=created_at,
        completed_at=completed_at,
        company_profile=company_profile,
        scope=scope,
        control_evaluations=evaluations,
        findings=findings,
        remediation_items=remediation_items,
        summary=summary,
        prior_historical_context=prior_historical_context or {},
        metadata=metadata or {},
    )


def build_report_pack(result: DeterministicAuditResult) -> dict[str, Any]:
    if not isinstance(result, DeterministicAuditResult):
        raise ValueError("result must be DeterministicAuditResult")

    findings = []
    for finding in result.findings:
        findings.append(
            {
                "finding_id": finding.finding_id,
                "control_id": finding.control_id,
                "regime_id": finding.regime_id,
                "title": finding.title,
                "severity": finding.severity.value,
                "status": finding.status.value,
                "verdict": finding.verdict.value,
                "missing_evidence_types": finding.missing_evidence_types,
                "evidence_refs": [asdict(ref) for ref in finding.evidence_refs],
                "rationale": finding.rationale,
                "remediation_actions": finding.remediation_actions,
            }
        )

    controls = []
    for row in result.control_evaluations:
        controls.append(
            {
                "control_id": row.control_id,
                "regime_id": row.regime_id,
                "verdict": row.verdict.value,
                "evidence_coverage_ratio": row.evidence_coverage_ratio,
                "evidence_refs": [asdict(ref) for ref in row.evidence_refs],
                "rationale": row.rationale,
            }
        )

    return {
        "report_pack_version": "v1",
        "generated_at": utc_now_iso(),
        "run_id": result.run_id,
        "company_profile": asdict(result.company_profile),
        "scope": asdict(result.scope),
        "summary": asdict(result.summary),
        "controls": controls,
        "findings": findings,
        "remediation_items": [asdict(item) for item in result.remediation_items],
        "prior_historical_context": result.prior_historical_context,
        "metadata": result.metadata,
    }
