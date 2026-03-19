from __future__ import annotations

from core.audit_runtime import (
    AuditScope,
    CompanyProfile,
    ControlDefinition,
    ControlInput,
    DeploymentDecision,
    EvidenceReference,
    EvidenceVerdict,
    FindingSeverity,
    OverallPosture,
    build_report_pack,
    evaluate_control,
    run_deterministic_audit,
    summarize_audit,
)


def make_company_profile() -> CompanyProfile:
    return CompanyProfile(
        company_name="Acme Fintech",
        industry="fintech",
        primary_jurisdiction="uk",
        additional_jurisdictions=["eu"],
        products=["payments"],
        entities=["Acme Fintech Ltd"],
    )


def make_scope() -> AuditScope:
    return AuditScope(
        audit_id="audit_001",
        audit_type="aml_readiness_review",
        framework_ids=["UK_MLR", "EU_AMLD6"],
        domain="aml",
        domains=["aml"],
        jurisdictions=["uk", "eu"],
        in_scope_entities=["Acme Fintech Ltd"],
        in_scope_products=["payments"],
        evaluation_date="2026-03-18",
        historical_context_is_non_authoritative=True,
        deterministic_current_audit_truth_only=True,
    )


def make_control() -> ControlDefinition:
    return ControlDefinition(
        control_id="AML.MONITORING.001",
        regime_id="UK_MLR.001",
        title="Transaction monitoring policy",
        description="A documented transaction monitoring control must exist.",
        test_procedure="Check for policy and monitoring evidence.",
        required_evidence_types=["policy_document", "monitoring_report"],
        severity_if_missing=FindingSeverity.HIGH,
    )


def test_evaluate_control_satisfied():
    control = make_control()
    evidence = [
        EvidenceReference(
            evidence_id="ev_001",
            title="Monitoring Policy",
            source_type="policy_document",
            file_path="evidence/policy.pdf",
            citation="policy.pdf#L1-L20",
        ),
        EvidenceReference(
            evidence_id="ev_002",
            title="Monitoring Report",
            source_type="monitoring_report",
            file_path="evidence/report.pdf",
            citation="report.pdf#L2-L12",
        ),
    ]
    result = evaluate_control(
        ControlInput(
            control=control,
            provided_evidence=evidence,
            declared_control_present=True,
            declared_operating_effective=True,
        )
    )
    assert result.verdict == EvidenceVerdict.SATISFIED
    assert result.evidence_coverage_ratio == 1.0
    assert result.findings == []


def test_evaluate_control_missing_evidence():
    control = make_control()
    evidence = [
        EvidenceReference(
            evidence_id="ev_001",
            title="Monitoring Policy",
            source_type="policy_document",
            file_path="evidence/policy.pdf",
            citation="policy.pdf#L1-L20",
        ),
    ]
    result = evaluate_control(
        ControlInput(
            control=control,
            provided_evidence=evidence,
            declared_control_present=True,
            declared_operating_effective=True,
        )
    )
    assert result.verdict == EvidenceVerdict.PARTIAL
    assert result.evidence_coverage_ratio == 0.5
    assert len(result.findings) == 1
    assert result.findings[0].missing_evidence_types == ["monitoring_report"]


def test_summarize_audit_red_when_failed():
    control = make_control()
    result = evaluate_control(
        ControlInput(
            control=control,
            provided_evidence=[],
            declared_control_present=False,
            declared_operating_effective=None,
        )
    )
    summary = summarize_audit([result])
    assert summary.overall_posture == OverallPosture.RED
    assert summary.deployment_decision == DeploymentDecision.BLOCKED


def test_run_deterministic_audit_and_report_pack():
    control = make_control()
    evidence = [
        EvidenceReference(
            evidence_id="ev_001",
            title="Monitoring Policy",
            source_type="policy_document",
            file_path="evidence/policy.pdf",
            citation="policy.pdf#L1-L20",
        )
    ]

    result = run_deterministic_audit(
        run_id="run_001",
        company_profile=make_company_profile(),
        scope=make_scope(),
        control_inputs=[
            ControlInput(
                control=control,
                provided_evidence=evidence,
                declared_control_present=True,
                declared_operating_effective=True,
            )
        ],
        default_remediation_owner="compliance@acme.com",
        prior_historical_context={"prior_findings": 2},
        metadata={"source": "unit_test"},
    )

    pack = build_report_pack(result)
    assert result.summary.control_count == 1
    assert len(result.findings) == 1
    assert len(result.remediation_items) == 1
    assert pack["summary"]["deployment_decision"] == "CONDITIONALLY_APPROVED"
    assert pack["prior_historical_context"] == {"prior_findings": 2}
    assert pack["metadata"] == {"source": "unit_test"}
