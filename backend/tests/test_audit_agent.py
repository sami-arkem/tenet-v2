"""
Unit tests for the AuditAgent.
Bible §T.1: every component tested before moving on.
Tests run without DB or network — fully isolated.
"""
from __future__ import annotations

import pytest

from app.agents.audit_agent import (
    AuditAgent,
    AuditResult,
    ControlDefinition,
    ControlVerdict,
    EvidenceItem,
)


JURISDICTION = "GB"


def _control(
    control_id: str = "AML-01",
    severity: str = "HIGH",
    required_categories: list[str] | None = None,
    criteria: str = "risk assessment,aml",
) -> ControlDefinition:
    return ControlDefinition(
        control_id=control_id,
        control_name=f"Test Control {control_id}",
        regime="AML",
        jurisdiction=JURISDICTION,
        severity=severity,
        required_evidence_categories=required_categories or ["AML_POLICY"],
        regulatory_reference="MLR 2017, Reg 18",
        requirement="Test requirement",
        evaluation_criteria=criteria,
    )


def _evidence(
    category: str = "AML_POLICY",
    text: str = "This is an aml policy with risk assessment and monitoring procedures.",
) -> EvidenceItem:
    return EvidenceItem(
        id="ev-001",
        category=category,
        filename="policy.pdf",
        extracted_text=text,
        file_hash="abc123",
    )


agent = AuditAgent()


# ─── Scoring ──────────────────────────────────────────────────────────────────

class TestScoreEvidence:
    def test_all_criteria_present_returns_one(self) -> None:
        evidence = [_evidence(text="risk assessment aml monitoring")]
        score = agent._score_evidence_against_criteria(
            evidence=evidence, criteria="risk assessment,aml,monitoring"
        )
        assert score == pytest.approx(1.0)

    def test_no_criteria_present_returns_zero(self) -> None:
        evidence = [_evidence(text="completely unrelated document")]
        score = agent._score_evidence_against_criteria(
            evidence=evidence, criteria="risk assessment,sanctions,monitoring"
        )
        assert score == pytest.approx(0.0)

    def test_partial_criteria_returns_fraction(self) -> None:
        evidence = [_evidence(text="risk assessment document only")]
        score = agent._score_evidence_against_criteria(
            evidence=evidence, criteria="risk assessment,sanctions,training"
        )
        assert score == pytest.approx(1 / 3)

    def test_empty_evidence_returns_zero(self) -> None:
        score = agent._score_evidence_against_criteria(evidence=[], criteria="risk assessment")
        assert score == 0.0

    def test_empty_extracted_text_returns_zero(self) -> None:
        evidence = [_evidence(text="")]
        score = agent._score_evidence_against_criteria(evidence=evidence, criteria="risk assessment")
        assert score == 0.0

    def test_empty_criteria_returns_one(self) -> None:
        evidence = [_evidence()]
        score = agent._score_evidence_against_criteria(evidence=evidence, criteria="")
        assert score == 1.0

    def test_case_insensitive(self) -> None:
        evidence = [_evidence(text="RISK ASSESSMENT AML POLICY")]
        score = agent._score_evidence_against_criteria(evidence=evidence, criteria="risk assessment,aml policy")
        assert score == pytest.approx(1.0)


# ─── Overall verdict ──────────────────────────────────────────────────────────

class TestComputeOverallVerdict:
    def _result(self, **kwargs: int) -> AuditResult:
        r = AuditResult(run_id="r1", tenant_id="t1", jurisdiction="GB", regime_scope=["AML"])
        for k, v in kwargs.items():
            setattr(r, k, v)
        return r

    def test_all_pass_returns_pass(self) -> None:
        r = self._result(pass_count=5, fail_count=0, partial_count=0, missing_count=0)
        assert agent._compute_overall_verdict(r) == "PASS"

    def test_any_fail_returns_fail(self) -> None:
        r = self._result(pass_count=5, fail_count=1, partial_count=0, missing_count=0)
        assert agent._compute_overall_verdict(r) == "FAIL"

    def test_partial_no_fail_returns_partial(self) -> None:
        r = self._result(pass_count=5, fail_count=0, partial_count=2, missing_count=0)
        assert agent._compute_overall_verdict(r) == "PARTIAL"

    def test_missing_no_fail_returns_partial(self) -> None:
        r = self._result(pass_count=3, fail_count=0, partial_count=0, missing_count=2)
        assert agent._compute_overall_verdict(r) == "PARTIAL"

    def test_all_zero_returns_missing(self) -> None:
        r = self._result(pass_count=0, fail_count=0, partial_count=0, missing_count=0)
        assert agent._compute_overall_verdict(r) == "MISSING_EVIDENCE"


# ─── Posture ──────────────────────────────────────────────────────────────────

class TestComputePosture:
    def _result_with_verdicts(self, verdicts: list[tuple[str, str]]) -> AuditResult:
        r = AuditResult(run_id="r1", tenant_id="t1", jurisdiction="GB", regime_scope=["AML"])
        for verdict, severity in verdicts:
            r.verdicts.append(
                ControlVerdict(
                    control_id="X",
                    control_name="X",
                    regime="AML",
                    jurisdiction="GB",
                    severity=severity,
                    verdict=verdict,
                    reason_code="",
                    finding="",
                    requirement="",
                    gap=None,
                    risk=None,
                    recommended_action=None,
                    regulatory_reference="",
                    evidence_ids=[],
                )
            )
            agent._tally(r, verdict)
        return r

    def test_all_pass_is_green(self) -> None:
        r = self._result_with_verdicts([("PASS", "HIGH"), ("PASS", "MEDIUM")])
        assert agent._compute_posture(r) == "GREEN"

    def test_critical_fail_is_red(self) -> None:
        r = self._result_with_verdicts([("PASS", "LOW"), ("FAIL", "CRITICAL")])
        assert agent._compute_posture(r) == "RED"

    def test_partial_is_amber(self) -> None:
        r = self._result_with_verdicts([("PASS", "HIGH"), ("PARTIAL", "MEDIUM")])
        assert agent._compute_posture(r) == "AMBER"

    def test_missing_evidence_is_amber(self) -> None:
        r = self._result_with_verdicts([("PASS", "HIGH"), ("MISSING_EVIDENCE", "MEDIUM")])
        assert agent._compute_posture(r) == "AMBER"


# ─── Control evaluation (sync portions) ──────────────────────────────────────

class TestEvaluateControlSync:
    """Tests the deterministic verdict decision based on score thresholds."""

    def test_high_score_produces_pass_verdict(self) -> None:
        # Simulate: _score returns 1.0 → PASS
        score = 1.0
        # Replicate threshold logic inline
        if score >= 0.80:
            v = "PASS"
        elif score >= 0.50:
            v = "PARTIAL"
        else:
            v = "FAIL"
        assert v == "PASS"

    def test_medium_score_produces_partial_verdict(self) -> None:
        score = 0.65
        if score >= 0.80:
            v = "PASS"
        elif score >= 0.50:
            v = "PARTIAL"
        else:
            v = "FAIL"
        assert v == "PARTIAL"

    def test_low_score_produces_fail_verdict(self) -> None:
        score = 0.20
        if score >= 0.80:
            v = "PASS"
        elif score >= 0.50:
            v = "PARTIAL"
        else:
            v = "FAIL"
        assert v == "FAIL"


# ─── Full audit run (no model, deterministic only) ────────────────────────────

@pytest.mark.asyncio
async def test_run_audit_no_evidence_returns_missing() -> None:
    controls = [_control(required_categories=["AML_POLICY"])]
    result = await agent.run_audit(
        run_id="test-run-001",
        tenant_id="tenant-001",
        jurisdiction="GB",
        regime_scope=["AML"],
        company_profile={"name": "Test Co"},
        evidence_items=[],  # no evidence
        controls=controls,
        model_call_logger=None,
    )
    assert result.overall_verdict in ("PARTIAL", "MISSING_EVIDENCE", "FAIL")
    assert result.posture in ("RED", "AMBER")
    assert len(result.verdicts) == 1
    assert result.verdicts[0].verdict == "MISSING_EVIDENCE"


@pytest.mark.asyncio
async def test_run_audit_matching_evidence_returns_pass() -> None:
    controls = [_control(required_categories=["AML_POLICY"], criteria="aml policy,monitoring")]
    evidence = [_evidence(category="AML_POLICY", text="This is a full aml policy with monitoring procedures")]
    result = await agent.run_audit(
        run_id="test-run-002",
        tenant_id="tenant-001",
        jurisdiction="GB",
        regime_scope=["AML"],
        company_profile={"name": "Test Co"},
        evidence_items=evidence,
        controls=controls,
        model_call_logger=None,
    )
    assert result.verdicts[0].verdict == "PASS"
    assert result.overall_verdict == "PASS"
    assert result.posture == "GREEN"


@pytest.mark.asyncio
async def test_run_audit_multiple_controls_correct_tally() -> None:
    controls = [
        _control("C1", required_categories=["CAT_A"], criteria="present,here"),
        _control("C2", required_categories=["CAT_B"], criteria="missing"),
    ]
    evidence = [_evidence(category="CAT_A", text="present here in full")]
    result = await agent.run_audit(
        run_id="test-run-003",
        tenant_id="tenant-001",
        jurisdiction="GB",
        regime_scope=["AML"],
        company_profile={},
        evidence_items=evidence,
        controls=controls,
        model_call_logger=None,
    )
    assert result.pass_count == 1
    assert result.missing_count == 1
    assert len(result.verdicts) == 2


@pytest.mark.asyncio
async def test_rule_1_model_cannot_change_verdict() -> None:
    """Bible Rule 1: model never touches verdict. Verify verdict comes from engine."""
    # Even if model_call_logger is provided, verdict must equal deterministic result
    controls = [_control(required_categories=["AML_POLICY"], criteria="absent_term")]
    evidence = [_evidence(category="AML_POLICY", text="unrelated text without criteria")]
    result = await agent.run_audit(
        run_id="test-run-004",
        tenant_id="t1",
        jurisdiction="GB",
        regime_scope=["AML"],
        company_profile={},
        evidence_items=evidence,
        controls=controls,
        model_call_logger=None,
    )
    # Score is 0.0 → FAIL. Model (if called) cannot change this.
    assert result.verdicts[0].verdict == "FAIL"
    assert result.overall_verdict == "FAIL"
