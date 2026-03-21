"""
Tenet Audit Agent — Bible §6.
The core compliance AI agent.

Bible Rules:
  Rule 1: Verdict is ALWAYS deterministic Python logic. Model never touches verdict.
  Rule 2: Every conclusion traces to evidence item, control, reason_code, regulatory ref.
  Rule 6: Every model call is logged to model_calls table with tokens and latency.

Architecture:
  1. Deterministic control evaluation (Python logic, no model)
  2. Model call for narrative/explanation only (never for verdict)
  3. Hard timeouts: classification 30s, explanation 45s, narrative 60s
  4. On timeout: fallback template, log as timeout, no error shown to user
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic

from app.config import settings

logger = logging.getLogger("tenet.audit_agent")

# ─── Control definition registry ─────────────────────────────────────────────
# In production this comes from the gold case library (database).
# Stub here represents structure.

@dataclass
class ControlDefinition:
    control_id: str
    control_name: str
    regime: str
    jurisdiction: str
    severity: str                       # CRITICAL | HIGH | MEDIUM | LOW
    required_evidence_categories: list[str]
    regulatory_reference: str
    requirement: str
    evaluation_criteria: str            # Deterministic criteria for PASS verdict


@dataclass
class EvidenceItem:
    id: str
    category: str
    filename: str
    extracted_text: str
    file_hash: str


@dataclass
class ControlVerdict:
    control_id: str
    control_name: str
    regime: str
    jurisdiction: str
    severity: str
    verdict: str                        # PASS | PARTIAL | FAIL | MISSING_EVIDENCE | NOT_APPLICABLE
    reason_code: str                    # machine-readable
    finding: str                        # human-readable gap
    requirement: str
    gap: str | None
    risk: str | None
    recommended_action: str | None
    regulatory_reference: str
    evidence_ids: list[str]
    model_call_id: str | None = None    # logged per Rule 6


@dataclass
class AuditResult:
    run_id: str
    tenant_id: str
    jurisdiction: str
    regime_scope: list[str]
    verdicts: list[ControlVerdict] = field(default_factory=list)
    pass_count: int = 0
    partial_count: int = 0
    fail_count: int = 0
    missing_count: int = 0
    na_count: int = 0
    overall_verdict: str | None = None
    posture: str | None = None          # GREEN | AMBER | RED
    error: str | None = None


class AuditAgent:
    """
    Bible §6: The core audit execution agent.

    Runs the full compliance audit against uploaded evidence.
    Verdict logic is 100% deterministic Python.
    Model is used only for narrative generation (never for scoring).
    """

    # Hard timeouts per Bible Rule 6
    CLASSIFICATION_TIMEOUT = 30
    EXPLANATION_TIMEOUT = 45
    NARRATIVE_TIMEOUT = 60

    def __init__(self) -> None:
        self._client: anthropic.AsyncAnthropic | None = None
        if settings.ANTHROPIC_API_KEY:
            self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def run_audit(
        self,
        *,
        run_id: str,
        tenant_id: str,
        jurisdiction: str,
        regime_scope: list[str],
        company_profile: dict[str, Any],
        evidence_items: list[EvidenceItem],
        controls: list[ControlDefinition],
        model_call_logger: Any | None = None,  # callable to log model calls
    ) -> AuditResult:
        """
        Execute a full compliance audit.
        Returns AuditResult with all verdicts and aggregate posture.
        """
        result = AuditResult(
            run_id=run_id,
            tenant_id=tenant_id,
            jurisdiction=jurisdiction,
            regime_scope=regime_scope,
        )

        evidence_by_category: dict[str, list[EvidenceItem]] = {}
        for item in evidence_items:
            evidence_by_category.setdefault(item.category, []).append(item)

        for control in controls:
            try:
                verdict = await self._evaluate_control(
                    control=control,
                    evidence_by_category=evidence_by_category,
                    company_profile=company_profile,
                    run_id=run_id,
                    tenant_id=tenant_id,
                    model_call_logger=model_call_logger,
                )
                result.verdicts.append(verdict)
                self._tally(result, verdict.verdict)
            except Exception as exc:
                logger.exception("Control %s evaluation failed: %s", control.control_id, exc)
                # Never crash the whole audit — mark as FAIL with error reason
                result.verdicts.append(
                    ControlVerdict(
                        control_id=control.control_id,
                        control_name=control.control_name,
                        regime=control.regime,
                        jurisdiction=control.jurisdiction,
                        severity=control.severity,
                        verdict="FAIL",
                        reason_code="EVALUATION_ERROR",
                        finding=f"Control evaluation encountered an error: {exc}",
                        requirement=control.requirement,
                        gap="Evaluation could not be completed",
                        risk="Unknown — manual review required",
                        recommended_action="Re-run audit after resolving the error",
                        regulatory_reference=control.regulatory_reference,
                        evidence_ids=[],
                    )
                )
                self._tally(result, "FAIL")

        result.overall_verdict = self._compute_overall_verdict(result)
        result.posture = self._compute_posture(result)
        return result

    # ─── Deterministic control evaluation ────────────────────────────────────
    # Bible Rule 1: model never touches this logic

    async def _evaluate_control(
        self,
        *,
        control: ControlDefinition,
        evidence_by_category: dict[str, list[EvidenceItem]],
        company_profile: dict[str, Any],
        run_id: str,
        tenant_id: str,
        model_call_logger: Any | None,
    ) -> ControlVerdict:
        # Step 1: Check required evidence categories exist
        available_evidence: list[EvidenceItem] = []
        missing_categories: list[str] = []

        for required_cat in control.required_evidence_categories:
            items = evidence_by_category.get(required_cat, [])
            if not items:
                missing_categories.append(required_cat)
            else:
                available_evidence.extend(items)

        if missing_categories:
            return ControlVerdict(
                control_id=control.control_id,
                control_name=control.control_name,
                regime=control.regime,
                jurisdiction=control.jurisdiction,
                severity=control.severity,
                verdict="MISSING_EVIDENCE",
                reason_code=f"MISSING_CATEGORY_{'_'.join(missing_categories)}",
                finding=f"Required evidence not found: {', '.join(missing_categories)}",
                requirement=control.requirement,
                gap=f"No {', '.join(missing_categories)} document uploaded",
                risk="Cannot assess compliance without this evidence",
                recommended_action=f"Upload a {', '.join(missing_categories)} document",
                regulatory_reference=control.regulatory_reference,
                evidence_ids=[item.id for item in available_evidence],
            )

        # Step 2: Score evidence content against evaluation criteria
        # Deterministic keyword/phrase matching — model only adds narrative
        score = self._score_evidence_against_criteria(
            evidence=available_evidence,
            criteria=control.evaluation_criteria,
        )

        # Step 3: Determine verdict deterministically based on score
        if score >= 0.80:
            verdict_str = "PASS"
            reason_code = "FULLY_SATISFIED"
            finding = f"{control.control_name} — all requirements satisfied"
            gap = None
            risk = None
            recommended_action = None
        elif score >= 0.50:
            verdict_str = "PARTIAL"
            reason_code = "PARTIALLY_SATISFIED"
            finding = f"{control.control_name} — partially satisfied"
            gap = "Some requirements not fully evidenced"
            risk = "Partial compliance may not satisfy regulator"
            recommended_action = "Strengthen evidence to fully satisfy all criteria"
        else:
            verdict_str = "FAIL"
            reason_code = "NOT_SATISFIED"
            finding = f"{control.control_name} — requirements not met"
            gap = "Evidence does not satisfy the control requirements"
            risk = "Non-compliance risk — regulatory action possible"
            recommended_action = "Address gaps identified and re-submit evidence"

        # Step 4: Model generates enriched narrative (Rule 6 — logged, bounded)
        model_call_id = None
        if self._client and verdict_str != "PASS":
            try:
                enriched, call_id = await self._generate_explanation(
                    control=control,
                    evidence=available_evidence,
                    verdict=verdict_str,
                    score=score,
                    run_id=run_id,
                    tenant_id=tenant_id,
                    model_call_logger=model_call_logger,
                )
                if enriched:
                    gap = enriched.get("gap", gap)
                    risk = enriched.get("risk", risk)
                    recommended_action = enriched.get("recommended_action", recommended_action)
                model_call_id = call_id
            except Exception as exc:
                # Rule 6: on timeout/error, use fallback — never show error to user
                logger.warning("Model explanation failed for %s: %s (using fallback)", control.control_id, exc)

        return ControlVerdict(
            control_id=control.control_id,
            control_name=control.control_name,
            regime=control.regime,
            jurisdiction=control.jurisdiction,
            severity=control.severity,
            verdict=verdict_str,
            reason_code=reason_code,
            finding=finding,
            requirement=control.requirement,
            gap=gap,
            risk=risk,
            recommended_action=recommended_action,
            regulatory_reference=control.regulatory_reference,
            evidence_ids=[item.id for item in available_evidence],
            model_call_id=model_call_id,
        )

    def _score_evidence_against_criteria(
        self,
        *,
        evidence: list[EvidenceItem],
        criteria: str,
    ) -> float:
        """
        Deterministic scoring: check how many criteria keywords appear in evidence.
        Returns 0.0–1.0. Model has zero involvement.

        In production this uses a more sophisticated but still deterministic
        presence-of-clauses algorithm against the gold case criteria spec.
        """
        if not evidence:
            return 0.0

        criteria_terms = [t.strip().lower() for t in criteria.split(",") if t.strip()]
        if not criteria_terms:
            return 1.0

        combined_text = " ".join(item.extracted_text.lower() for item in evidence if item.extracted_text)
        if not combined_text:
            return 0.0

        matched = sum(1 for term in criteria_terms if term in combined_text)
        return matched / len(criteria_terms)

    # ─── Model call for narrative only (Rule 6) ───────────────────────────────

    async def _generate_explanation(
        self,
        *,
        control: ControlDefinition,
        evidence: list[EvidenceItem],
        verdict: str,
        score: float,
        run_id: str,
        tenant_id: str,
        model_call_logger: Any | None,
    ) -> tuple[dict[str, str] | None, str | None]:
        """
        Ask Claude to enrich the gap/risk/recommendation narrative.
        Rule 1: verdict is ALREADY decided by Python logic above — model cannot change it.
        Rule 6: every call is logged with tokens and latency.
        """
        if not self._client:
            return None, None

        evidence_excerpts = "\n\n".join(
            f"[{item.category}] {item.filename}:\n{item.extracted_text[:2000]}"
            for item in evidence[:3]  # max 3 evidence items per control call
        )

        prompt = f"""You are a compliance analyst writing a brief explanation for an audit finding.

CONTROL: {control.control_name} ({control.control_id})
REGIME: {control.regime}
JURISDICTION: {control.jurisdiction}
REQUIREMENT: {control.requirement}
REGULATORY REFERENCE: {control.regulatory_reference}
VERDICT (already determined by audit engine): {verdict}
COMPLIANCE SCORE: {score:.0%}

EVIDENCE REVIEWED:
{evidence_excerpts}

Write exactly 3 short fields (JSON only, no preamble):
{{
  "gap": "one sentence describing the specific gap in the evidence (if FAIL/PARTIAL)",
  "risk": "one sentence on the regulatory risk if not addressed",
  "recommended_action": "one concrete action to remediate"
}}

Rules:
- Never state a different verdict — the verdict above is final and determined by the audit engine
- Never say "the AI determined" — write as the audit system
- Be specific and regulatory-reference aware
- Maximum 40 words per field"""

        start = time.perf_counter()
        prompt_tokens = 0
        completion_tokens = 0
        timed_out = False
        error_str = None

        try:
            response = await asyncio.wait_for(
                self._client.messages.create(
                    model=settings.ANTHROPIC_MODEL,
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}],
                ),
                timeout=self.EXPLANATION_TIMEOUT,
            )
            prompt_tokens = response.usage.input_tokens
            completion_tokens = response.usage.output_tokens
            raw = response.content[0].text.strip()

            import json
            # Strip any markdown code fences
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            enriched: dict[str, str] = json.loads(raw)

        except TimeoutError:
            timed_out = True
            enriched = {}
            error_str = "TIMEOUT"
        except Exception as exc:
            enriched = {}
            error_str = str(exc)[:200]

        latency_ms = int((time.perf_counter() - start) * 1000)

        call_id = None
        if model_call_logger:
            try:
                call_id = await model_call_logger(
                    tenant_id=tenant_id,
                    audit_run_id=run_id,
                    control_id=control.control_id,
                    call_type="explanation",
                    model=settings.ANTHROPIC_MODEL,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                    timed_out=timed_out,
                    error=error_str,
                )
            except Exception as exc:
                logger.warning("Failed to log model call: %s", exc)

        return (enriched if enriched else None), call_id

    # ─── Aggregate scoring ────────────────────────────────────────────────────

    def _compute_overall_verdict(self, result: AuditResult) -> str:
        """Deterministic overall verdict from individual control verdicts."""
        if result.fail_count > 0:
            return "FAIL"
        if result.partial_count > 0 or result.missing_count > 0:
            return "PARTIAL"
        if result.pass_count > 0:
            return "PASS"
        return "MISSING_EVIDENCE"

    def _compute_posture(self, result: AuditResult) -> str:
        """Deterministic posture: GREEN / AMBER / RED."""
        total = result.pass_count + result.partial_count + result.fail_count + result.missing_count
        if total == 0:
            return "AMBER"

        critical_fails = sum(
            1 for v in result.verdicts
            if v.verdict in ("FAIL", "MISSING_EVIDENCE") and v.severity == "CRITICAL"
        )
        if critical_fails > 0 or result.fail_count > total * 0.30:
            return "RED"
        if result.partial_count > 0 or result.missing_count > 0:
            return "AMBER"
        return "GREEN"

    def _tally(self, result: AuditResult, verdict: str) -> None:
        match verdict:
            case "PASS":            result.pass_count += 1
            case "PARTIAL":         result.partial_count += 1
            case "FAIL":            result.fail_count += 1
            case "MISSING_EVIDENCE": result.missing_count += 1
            case "NOT_APPLICABLE":  result.na_count += 1
