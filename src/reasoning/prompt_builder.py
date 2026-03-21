from __future__ import annotations

import json
from typing import Any, Dict, List


OVERLAY_OUTPUT_CONTRACT = {
    "executive_summary": {
        "system_or_business_reviewed": "",
        "overall_readiness": "",
        "top_issues": [],
        "decision_summary": "",
        "board_message": ""
    },
    "reporting_outputs": {
        "board_ready_summary": "",
        "regulator_ready_summary": "",
        "client_facing_summary": ""
    }
}


def _compact_chunk(chunk: Dict[str, Any], max_chars: int = 450) -> Dict[str, Any]:
    text = str(chunk.get("text", "") or "")
    return {
        "chunk_id": chunk.get("chunk_id"),
        "document_name": chunk.get("document_name", ""),
        "source_name": chunk.get("source_name", ""),
        "source_family": chunk.get("source_family", ""),
        "jurisdiction": chunk.get("jurisdiction", ""),
        "audit_domain": chunk.get("audit_domain", ""),
        "score": chunk.get("score", 0),
        "text": text[:max_chars],
    }


def build_reasoning_messages(
    audit_context: Dict[str, Any],
    audit_plan: Dict[str, Any],
    retrieved_chunks: List[Dict[str, Any]],
    output_schema_template: Dict[str, Any] | None = None,
) -> List[Dict[str, str]]:
    system = """
You are Tenet, a regulator-grade compliance reasoning engine.

You are generating ONLY two narrative sections for a deterministic audit engine: executive_summary and reporting_outputs.

Rules:
- Use only the provided context, audit plan, deterministic baseline, and retrieved evidence.
- Do not invent facts.
- Keep missing controls separate from missing evidence.
- Preserve citations and control_ids where relevant.
- Return valid JSON only.
- Return ONLY these sections:
  executive_summary
  reporting_outputs
""".strip()

    payload = {
        "audit_context": {
            "audit_type": audit_context.get("audit_type"),
            "industry": audit_context.get("industry"),
            "jurisdictions": audit_context.get("jurisdictions"),
            "entity_name": audit_context.get("entity_name"),
            "entity_type": audit_context.get("entity_type"),
            "products": audit_context.get("products", []),
            "customer_types": audit_context.get("customer_types", []),
        },
        "audit_plan": {
            "applicable_regimes": audit_plan.get("applicable_regimes", []),
            "review_focus": audit_plan.get("review_focus", []),
            "required_control_ids": audit_plan.get("required_control_ids", []),
            "decision_sensitivity": audit_plan.get("decision_sensitivity", ""),
        },
        "retrieved_evidence": [_compact_chunk(chunk) for chunk in retrieved_chunks[:3]],
        "output_contract": OVERLAY_OUTPUT_CONTRACT,
        "instructions": [
            "Generate concise, evidence-grounded narrative overlay sections only.",
            "Do not output any section outside the overlay contract.",
            "Do not restate the whole audit object.",
            "Prefer short, regulator-ready language."
        ],
    }

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def build_retrieval_followup_messages(
    known_context: Dict[str, Any],
    retrieved_chunks: List[Dict[str, Any]],
    missing_fields: List[str],
) -> List[Dict[str, str]]:
    system = """
You are Tenet's AI intake strategist.
Ask exactly one short, high-value follow-up question.
Return JSON only.
""".strip()

    payload = {
        "known_context": known_context,
        "retrieved_evidence": [_compact_chunk(chunk, max_chars=300) for chunk in retrieved_chunks[:2]],
        "missing_fields": missing_fields,
    }

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
