from __future__ import annotations

from typing import Any

from core.model_manager import (
    CALL_TYPE_DOCUMENT_CLASSIFICATION,
    CALL_TYPE_EXECUTIVE_NARRATIVE,
    CALL_TYPE_GAP_EXPLANATION,
    CALL_TYPE_KEY_FACT_EXTRACTION,
    ModelManager,
    NON_AUTHORITATIVE_LABEL,
)


def classify_document(
    *,
    filename: str,
    extracted_text: str,
    model_manager: ModelManager | None = None,
) -> dict[str, Any]:
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("filename must be non-empty string")
    if not isinstance(extracted_text, str) or not extracted_text.strip():
        raise ValueError("extracted_text must be non-empty string")

    mm = model_manager or ModelManager()
    system_prompt = (
        "You classify compliance evidence documents. "
        "Return JSON only with keys: category, confidence, reason. "
        "Allowed confidence values: HIGH, MEDIUM, LOW, MANUAL, UNCLASSIFIED. "
        "This output is non-authoritative and cannot decide any verdict."
    )
    user_prompt = (
        "Classify document.\n"
        f"Filename: {filename}\n"
        "Text excerpt:\n"
        f"{extracted_text[:3000]}"
    )
    out = mm.call_json(
        call_type=CALL_TYPE_DOCUMENT_CLASSIFICATION,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_output_tokens=300,
        timeout_seconds=30,
    )
    out["label"] = NON_AUTHORITATIVE_LABEL
    return out


def extract_key_facts(
    *,
    category: str,
    extracted_text: str,
    model_manager: ModelManager | None = None,
) -> dict[str, Any]:
    if not isinstance(category, str) or not category.strip():
        raise ValueError("category must be non-empty string")
    if not isinstance(extracted_text, str) or not extracted_text.strip():
        raise ValueError("extracted_text must be non-empty string")

    mm = model_manager or ModelManager()
    system_prompt = (
        "You extract key facts from compliance evidence. "
        "Return JSON only with one key: facts. "
        "The output must be non-authoritative and strictly descriptive."
    )
    user_prompt = (
        "Extract key facts.\n"
        f"Category: {category}\n"
        "Text excerpt:\n"
        f"{extracted_text[:5000]}"
    )
    out = mm.call_json(
        call_type=CALL_TYPE_KEY_FACT_EXTRACTION,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_output_tokens=600,
        timeout_seconds=45,
    )
    out["label"] = NON_AUTHORITATIVE_LABEL
    return out


def explain_gap(
    *,
    finding: dict[str, Any],
    requirement_text: str,
    model_manager: ModelManager | None = None,
) -> dict[str, Any]:
    if not isinstance(finding, dict):
        raise ValueError("finding must be object")
    if not isinstance(requirement_text, str) or not requirement_text.strip():
        raise ValueError("requirement_text must be non-empty string")

    mm = model_manager or ModelManager()
    system_prompt = (
        "You explain a compliance gap using only supplied deterministic facts. "
        "You do not alter verdicts. "
        "Return JSON only with key: narrative."
    )
    user_prompt = (
        "Explain compliance gap.\n"
        f"Requirement: {requirement_text}\n"
        f"Finding JSON: {finding}\n"
        "Write concise regulator-grade narrative from these deterministic facts only."
    )

    try:
        out = mm.call_json(
            call_type=CALL_TYPE_GAP_EXPLANATION,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_output_tokens=500,
            timeout_seconds=45,
        )
        out["label"] = NON_AUTHORITATIVE_LABEL
        return out
    except Exception:
        return {
            "narrative": (
                f"GAP: Deterministic audit found a control or evidence deficiency. "
                f"REQUIREMENT: {requirement_text}. "
                f"FINDING: {finding.get('title') or finding.get('finding_id') or 'Unspecified finding'}. "
                "ACTION: Review missing evidence, remediate control weakness, and retest."
            ),
            "label": NON_AUTHORITATIVE_LABEL,
            "fallback_used": True,
        }


def write_executive_narrative(
    *,
    summary: dict[str, Any],
    highlights: list[dict[str, Any]],
    model_manager: ModelManager | None = None,
) -> dict[str, Any]:
    if not isinstance(summary, dict):
        raise ValueError("summary must be object")
    if not isinstance(highlights, list):
        raise ValueError("highlights must be list")

    mm = model_manager or ModelManager()
    system_prompt = (
        "You write an executive compliance narrative from deterministic facts only. "
        "You must not invent verdicts or change posture. "
        "Return JSON only with key: narrative."
    )
    user_prompt = (
        "Write executive narrative.\n"
        f"Summary JSON: {summary}\n"
        f"Highlights JSON: {highlights[:20]}\n"
        "Keep it concise, board-ready, and grounded in the supplied facts."
    )

    try:
        out = mm.call_json(
            call_type=CALL_TYPE_EXECUTIVE_NARRATIVE,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_output_tokens=700,
            timeout_seconds=60,
        )
        out["label"] = NON_AUTHORITATIVE_LABEL
        return out
    except Exception:
        return {
            "narrative": (
                f"Deterministic audit posture: {summary.get('overall_posture')}. "
                f"Deployment decision: {summary.get('deployment_decision')}. "
                "Review the structured findings and remediation plan for exact control-level actions."
            ),
            "label": NON_AUTHORITATIVE_LABEL,
            "fallback_used": True,
        }
