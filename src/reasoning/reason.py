from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.contracts import validate_audit_context
from src.core.pack_runtime import build_runtime_retrieval_query, enrich_audit_plan_with_packs
from src.reasoning.audit_plan import build_audit_plan, audit_plan_to_dict
from src.reasoning.control_eval import evaluate_controls, summarize_gaps
from src.reasoning.decision import decide_deployment
from src.reasoning.model_reasoner import ModelReasoner, ModelReasonerError
from src.reasoning.schema import OUTPUT_SCHEMA_TEMPLATE
from src.retrieval.retrieve import retrieve


RUNTIME_CONFIG_PATH = Path("data/config/reasoning_runtime_v1.json")


def load_runtime_config(path: Path = RUNTIME_CONFIG_PATH) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_audit_context(audit_context: Dict[str, Any]) -> Dict[str, Any]:
    ctx = copy.deepcopy(audit_context)
    if "audit_type" in ctx and isinstance(ctx["audit_type"], str):
        ctx["audit_type"] = ctx["audit_type"].strip().lower()
    if "industry" in ctx and isinstance(ctx["industry"], str):
        ctx["industry"] = ctx["industry"].strip().lower()
    if "jurisdictions" in ctx and isinstance(ctx["jurisdictions"], list):
        ctx["jurisdictions"] = [str(j).strip().upper() for j in ctx["jurisdictions"]]
    return ctx


def _build_retrieval_query(audit_context: Dict[str, Any], audit_plan: Any) -> str:
    parts: List[str] = []

    for key in ["audit_type", "industry", "entity_name", "business_model"]:
        value = audit_context.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.replace("_", " "))

    for key in [
        "jurisdictions",
        "products",
        "customer_types",
        "distribution_channels",
        "payment_flows",
        "high_risk_activities",
        "query_terms",
    ]:
        value = audit_context.get(key, [])
        if isinstance(value, list):
            parts.extend(str(x) for x in value if x)

    parts.extend(audit_plan.applicable_regimes)
    parts.extend(audit_plan.review_focus)
    parts.extend(audit_plan.required_evidence_types)

    return " ".join(str(p) for p in parts if p).strip()


def _chunk_to_evidence_item(chunk: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "chunk_id": chunk.get("chunk_id"),
        "document_name": chunk.get("document_name", ""),
        "source_name": chunk.get("source_name", ""),
        "source_family": chunk.get("source_family", ""),
        "jurisdiction": chunk.get("jurisdiction", ""),
        "industry": chunk.get("industry", ""),
        "audit_domain": chunk.get("audit_domain", ""),
        "url": chunk.get("url", ""),
        "score": chunk.get("score", 0),
        "quality_status": chunk.get("quality_status", ""),
        "excerpt": str(chunk.get("text", "") or "")[:500],
    }


def _derive_findings(control_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    counter = 1
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    actionable = [r for r in control_results if r.get("status") in {"missing", "partial", "unknown"}]
    ordered = sorted(
        actionable,
        key=lambda x: (
            severity_rank.get(x.get("severity_if_missing", "low"), 1),
            3 if x.get("status") == "missing" else 2 if x.get("status") == "partial" else 1,
            -float(x.get("confidence", 0.0)),
        ),
        reverse=True,
    )

    for result in ordered:
        findings.append(
            {
                "finding_id": f"F-{counter:03d}",
                "title": result.get("title", ""),
                "domain": result.get("domain", ""),
                "severity": str(result.get("severity_if_missing", "")).upper(),
                "status": str(result.get("status", "")).upper(),
                "description": result.get("rationale", ""),
                "citations": result.get("citations", []),
                "control_id": result.get("control_id", ""),
            }
        )
        counter += 1

    return findings


def _derive_key_risks(control_results: List[Dict[str, Any]], findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    risks: List[Dict[str, Any]] = []
    linked_finding_ids = [f["finding_id"] for f in findings]

    for idx, result in enumerate(control_results, start=1):
        if result["status"] == "met":
            continue
        if result["severity_if_missing"] not in {"critical", "high"}:
            continue
        risks.append(
            {
                "risk_id": f"R-{idx:03d}",
                "risk_title": result["title"],
                "category": result["domain"],
                "description": result["rationale"],
                "severity": result["severity_if_missing"].upper(),
                "linked_findings": linked_finding_ids[:3],
            }
        )

    return risks


def _build_remediation_roadmap(control_results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    buckets = {
        "immediate_0_30_days": [],
        "near_term_30_90_days": [],
        "medium_term_90_180_days": [],
        "strategic_180_plus_days": [],
    }

    for result in control_results:
        if result["status"] == "met":
            continue

        item = {
            "control_id": result["control_id"],
            "title": result["title"],
            "domain": result["domain"],
            "priority": result["severity_if_missing"].upper(),
            "action": f"Remediate and evidence control: {result['title']}",
        }

        severity = result["severity_if_missing"]
        if severity == "critical":
            buckets["immediate_0_30_days"].append(item)
        elif severity == "high":
            buckets["near_term_30_90_days"].append(item)
        elif severity == "medium":
            buckets["medium_term_90_180_days"].append(item)
        else:
            buckets["strategic_180_plus_days"].append(item)

    return buckets


def _compute_control_coverage_score(control_results: List[Dict[str, Any]]) -> int:
    if not control_results:
        return 0
    weights = {"met": 1.0, "partial": 0.6, "unknown": 0.35, "missing": 0.0}
    score = sum(weights.get(r["status"], 0.0) for r in control_results) / len(control_results)
    return round(score * 100)


def _compute_evidence_coverage_score(control_results: List[Dict[str, Any]]) -> int:
    if not control_results:
        return 0
    weights = {"sufficient": 1.0, "partial": 0.5, "missing": 0.0, "not_reviewed": 0.0}
    score = sum(weights.get(r["evidence_status"], 0.0) for r in control_results) / len(control_results)
    return round(score * 100)


def _compute_confidence(control_results: List[Dict[str, Any]], retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not control_results:
        return {
            "overall_confidence_score": 0,
            "confidence_level": "LOW",
            "confidence_drivers": [],
            "limiting_factors": ["No control results produced"],
            "human_review_required": True,
        }

    avg_control_confidence = sum(float(r.get("confidence", 0.0)) for r in control_results) / len(control_results)
    retrieval_factor = min(len(retrieved_chunks) / 12.0, 1.0)
    overall_score = round(((avg_control_confidence * 0.8) + (retrieval_factor * 0.2)) * 100)

    if overall_score >= 80:
        confidence_level = "HIGH"
    elif overall_score >= 55:
        confidence_level = "MODERATE"
    else:
        confidence_level = "LOW"

    drivers = [
        f"{len(control_results)} required controls evaluated",
        f"{len(retrieved_chunks)} relevant chunks retrieved",
    ]
    limiting_factors = ["Human review remains mandatory for client-facing output"]
    if any(r["evidence_status"] in {"missing", "partial"} for r in control_results):
        limiting_factors.append("Evidence sufficiency remains incomplete for one or more controls")
    if any(r["status"] in {"missing", "unknown"} for r in control_results):
        limiting_factors.append("One or more required controls are not yet fully demonstrated")

    return {
        "overall_confidence_score": overall_score,
        "confidence_level": confidence_level,
        "confidence_drivers": drivers,
        "limiting_factors": limiting_factors,
        "human_review_required": True,
    }


def _build_deterministic_output(
    ctx: Dict[str, Any],
    audit_plan: Any,
    retrieved_chunks: List[Dict[str, Any]],
    control_results: List[Dict[str, Any]],
    gap_summary: Dict[str, Any],
    decision: Dict[str, Any],
) -> Dict[str, Any]:
    obj = copy.deepcopy(OUTPUT_SCHEMA_TEMPLATE)
    findings = _derive_findings(control_results)
    key_risks = _derive_key_risks(control_results, findings)
    confidence = _compute_confidence(control_results, retrieved_chunks)
    remediation_roadmap = _build_remediation_roadmap(control_results)

    obj["audit_meta"]["audit_id"] = ctx.get("audit_id", "")
    obj["audit_meta"]["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    obj["audit_meta"]["platform_version"] = "tenet-mvp"
    obj["audit_meta"]["model_version"] = ctx.get("model_version", "deterministic-reasoner-v1")
    obj["audit_meta"]["report_status"] = "draft"

    obj["entity_profile"]["legal_name"] = ctx.get("entity_name", "")
    obj["entity_profile"]["trade_name"] = ctx.get("trade_name", "")
    obj["entity_profile"]["industry"] = ctx.get("industry", "")
    obj["entity_profile"]["subindustry"] = ctx.get("subindustry", "")
    obj["entity_profile"]["business_model"] = ctx.get("business_model", "")
    obj["entity_profile"]["products_services"] = ctx.get("products", [])
    obj["entity_profile"]["jurisdictions_of_operation"] = ctx.get("jurisdictions", [])
    obj["entity_profile"]["customer_geographies"] = ctx.get("customer_geographies", [])
    obj["entity_profile"]["customer_types"] = ctx.get("customer_types", [])
    obj["entity_profile"]["distribution_channels"] = ctx.get("distribution_channels", [])
    obj["entity_profile"]["payment_flows"] = ctx.get("payment_flows", [])
    obj["entity_profile"]["data_categories_processed"] = ctx.get("data_categories_processed", [])
    obj["entity_profile"]["high_risk_activities"] = ctx.get("high_risk_activities", [])

    obj["audit_scope"]["audit_type"] = ctx["audit_type"]
    obj["audit_scope"]["scope_statement"] = f"{ctx['audit_type']} for {ctx['industry']} across {', '.join(ctx['jurisdictions'])}"
    obj["audit_scope"]["included_domains"] = audit_plan.review_focus
    obj["audit_scope"]["excluded_domains"] = ctx.get("excluded_domains", [])
    obj["audit_scope"]["documents_reviewed"] = sorted({c.get("document_name", "") for c in retrieved_chunks if c.get("document_name")})
    obj["audit_scope"]["evidence_received"] = sorted({c.get("document_name", "") for c in retrieved_chunks if c.get("document_name")})
    obj["audit_scope"]["evidence_missing_at_start"] = [x["title"] for x in gap_summary["missing_evidence"]]

    obj["regulatory_applicability"]["primary_regimes"] = audit_plan.applicable_regimes
    obj["regulatory_applicability"]["secondary_regimes"] = []
    obj["regulatory_applicability"]["frameworks"] = audit_plan.applicable_regimes
    obj["regulatory_applicability"]["licensing_obligations"] = []
    obj["regulatory_applicability"]["enforcement_exposure_areas"] = sorted({r["domain"] for r in control_results if r["status"] != "met"})
    obj["regulatory_applicability"]["regulatory_classification"]["entity_type"] = ctx.get("entity_type", "")
    obj["regulatory_applicability"]["regulatory_classification"]["risk_tier"] = "HIGH" if decision["decision"] == "BLOCKED" else "MODERATE"
    obj["regulatory_applicability"]["regulatory_classification"]["obligation_intensity"] = audit_plan.decision_sensitivity.upper()
    obj["regulatory_applicability"]["regulatory_classification"]["cross_border_complexity"] = "HIGH" if len(ctx["jurisdictions"]) > 1 else "MODERATE"

    obj["executive_summary"]["system_or_business_reviewed"] = ctx.get("entity_name", "") or ctx.get("audit_id", "")
    obj["executive_summary"]["overall_readiness"] = decision["decision"]
    obj["executive_summary"]["top_issues"] = [f["title"] for f in findings[:3]]
    obj["executive_summary"]["decision_summary"] = decision["rationale"]
    obj["executive_summary"]["board_message"] = (
        f"Tenet evaluated {len(control_results)} required controls across {len(audit_plan.applicable_regimes)} primary regimes. "
        f"Current decision: {decision['decision']}."
    )

    obj["deployment_decision"]["status"] = decision["decision"]
    obj["deployment_decision"]["decision_rationale"] = decision["rationale"]
    obj["deployment_decision"]["blocking_issues"] = [f["title"] for f in findings if f["severity"] == "CRITICAL"]
    obj["deployment_decision"]["conditions_precedent"] = [x["title"] for x in gap_summary["missing_evidence"][:10]]
    obj["deployment_decision"]["conditions_ongoing"] = [r["title"] for r in control_results if r["status"] == "partial"]

    exposure_band = "LOW"
    if decision["decision"] == "BLOCKED":
        exposure_band = "HIGH"
    elif decision["decision"] == "CONDITIONALLY_APPROVED":
        exposure_band = "MODERATE"

    obj["financial_exposure"]["estimated_regulatory_exposure"] = exposure_band
    obj["financial_exposure"]["exposure_band"] = exposure_band
    obj["financial_exposure"]["drivers"] = sorted({r["domain"] for r in control_results if r["status"] != "met"})
    obj["financial_exposure"]["assumptions"] = [
        "Exposure band is inferred from control severity, status, and evidence sufficiency",
        "Human review is required before external reliance",
    ]
    obj["financial_exposure"]["confidence_note"] = f"Derived from average control confidence score of {decision['average_confidence']}"

    obj["control_assessment"]["domains"] = control_results
    obj["control_assessment"]["control_coverage_score"] = _compute_control_coverage_score(control_results)
    obj["control_assessment"]["evidence_coverage_score"] = _compute_evidence_coverage_score(control_results)

    obj["findings"] = findings
    obj["key_risks"] = key_risks
    obj["missing_controls"] = gap_summary["missing_controls"]
    obj["missing_evidence"] = gap_summary["missing_evidence"]
    obj["remediation_roadmap"] = remediation_roadmap

    obj["reporting_outputs"]["board_ready_summary"] = obj["executive_summary"]["board_message"]
    obj["reporting_outputs"]["regulator_ready_summary"] = (
        f"Applicable regimes: {', '.join(audit_plan.applicable_regimes)}. "
        f"Decision: {decision['decision']}. "
        f"Missing controls: {len(obj['missing_controls'])}. Missing evidence items: {len(obj['missing_evidence'])}."
    )
    obj["reporting_outputs"]["client_facing_summary"] = (
        f"The current review outcome is {decision['decision']}. "
        f"{len(findings)} findings were identified and require human-reviewed remediation tracking."
    )

    obj["confidence_assessment"] = confidence
    obj["evidence_appendix"] = [_chunk_to_evidence_item(chunk) for chunk in retrieved_chunks]

    return obj


def _apply_model_overlay(
    deterministic_output: Dict[str, Any],
    model_output: Dict[str, Any],
    sections: List[str],
) -> Dict[str, Any]:
    merged = copy.deepcopy(deterministic_output)

    for section in sections:
        if section in deterministic_output and section in model_output:
            merged[section] = copy.deepcopy(model_output[section])

    if "executive_summary" in merged and isinstance(merged["executive_summary"], dict):
        if not merged["executive_summary"].get("overall_readiness"):
            merged["executive_summary"]["overall_readiness"] = deterministic_output["deployment_decision"]["status"]

    return merged


def _should_use_model_reasoning(runtime_config: Dict[str, Any], retrieved_chunks: List[Dict[str, Any]], reasoner: Optional[ModelReasoner]) -> bool:
    if not runtime_config.get("enable_model_reasoning", False):
        return False
    if reasoner is None or not reasoner.is_configured():
        return False
    if runtime_config.get("require_retrieved_chunks_for_model_reasoning", True) and not retrieved_chunks:
        return False
    return True


def reason(
    audit_context: Dict[str, Any],
    reasoner: Optional[ModelReasoner] = None,
    runtime_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ctx = _normalize_audit_context(audit_context)
    errors = validate_audit_context(ctx)
    if errors:
        raise ValueError("Invalid audit_context: " + " | ".join(errors))

    runtime = runtime_config or load_runtime_config()
    audit_plan = build_audit_plan(ctx)
    audit_plan = enrich_audit_plan_with_packs(ctx, audit_plan)

    retrieval_query = build_runtime_retrieval_query(ctx, audit_plan)
    retrieval_jurisdictions = [j.lower() for j in ctx.get("jurisdictions", [])]
    retrieved_chunks = retrieve(
        query=retrieval_query,
        industry=ctx.get("industry"),
        jurisdictions=retrieval_jurisdictions,
        source_families=ctx.get("source_families"),
        top_k=int(ctx.get("top_k", 12)),
    )

    control_results = evaluate_controls(audit_plan.required_control_ids, retrieved_chunks)
    gap_summary = summarize_gaps(control_results)
    decision = decide_deployment(control_results)

    deterministic_output = _build_deterministic_output(
        ctx=ctx,
        audit_plan=audit_plan,
        retrieved_chunks=retrieved_chunks,
        control_results=control_results,
        gap_summary=gap_summary,
        decision=decision,
    )

    deterministic_output["audit_meta"]["model_version"] = ctx.get("model_version", "deterministic-reasoner-v1")
    deterministic_output["audit_meta"]["reasoning_mode"] = "deterministic"

    if not _should_use_model_reasoning(runtime, retrieved_chunks, reasoner):
        return deterministic_output

    try:
        model_result = reasoner.reason(
            audit_context=ctx,
            audit_plan=audit_plan_to_dict(audit_plan),
            retrieved_chunks=retrieved_chunks,
            model_name=ctx.get("reasoning_model_name"),
        )
        final_output = _apply_model_overlay(
            deterministic_output=deterministic_output,
            model_output=model_result.output,
            sections=runtime.get("model_overlay_sections", []),
        )
        final_output["audit_meta"]["model_version"] = model_result.model_name
        final_output["audit_meta"]["reasoning_mode"] = "hybrid_model_overlay"
        if model_result.validation_errors:
            final_output["confidence_assessment"]["limiting_factors"].append(
                f"Model output required structural repair: {len(model_result.validation_errors)} adjustments"
            )
        return final_output
    except ModelReasonerError as exc:
        if runtime.get("fallback_to_deterministic_on_model_error", True):
            deterministic_output["audit_meta"]["reasoning_mode"] = "deterministic_fallback"
            deterministic_output["confidence_assessment"]["limiting_factors"].append(
                f"Model overlay unavailable; deterministic fallback used: {exc}"
            )
            return deterministic_output
        raise


def reason_from_normalized_intake(audit_context: Dict[str, Any]) -> Dict[str, Any]:
    return reason(audit_context)


if __name__ == "__main__":
    audit_context = {
        "audit_id": "demo-001",
        "entity_name": "Demo Entity",
        "industry": "fintech",
        "jurisdictions": ["US", "UK", "EU"],
        "audit_type": "aml_readiness_review",
        "source_families": ["regulations", "aml", "enforcement", "industry_fintech"],
        "query_terms": ["aml", "kyc", "sanctions", "customer due diligence", "controls", "governance"],
        "top_k": 12,
    }
    result = reason(audit_context)
    print(json.dumps(result, indent=2))
