from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.llm.model_adapter import ModelAdapter, ModelAdapterError, ModelRequest
from src.reasoning.prompt_builder import build_reasoning_messages
from src.reasoning.schema import OUTPUT_SCHEMA_TEMPLATE
from src.reasoning.schema_validator import repair_to_template, validate_exact_shape


class ModelReasonerError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelReasonerResult:
    output: Dict[str, Any]
    model_name: str
    provider: str
    repaired: bool
    validation_errors: List[str] = field(default_factory=list)
    model_metadata: Dict[str, Any] = field(default_factory=dict)


OVERLAY_SECTIONS = {
    "executive_summary",
    "reporting_outputs",
}


def _empty_overlay_shell(
    audit_context: Dict[str, Any],
    audit_plan: Dict[str, Any],
    retrieved_chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    obj = copy.deepcopy(OUTPUT_SCHEMA_TEMPLATE)
    obj["audit_scope"]["audit_type"] = audit_context.get("audit_type", "")
    obj["audit_scope"]["included_domains"] = list(audit_plan.get("review_focus", []))
    obj["regulatory_applicability"]["primary_regimes"] = list(audit_plan.get("applicable_regimes", []))
    obj["regulatory_applicability"]["frameworks"] = list(audit_plan.get("applicable_regimes", []))
    obj["evidence_appendix"] = [
        {
            "chunk_id": chunk.get("chunk_id", ""),
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
        for chunk in retrieved_chunks
    ]
    return obj


class ModelReasoner:
    def __init__(self, model_adapter: Optional[ModelAdapter] = None) -> None:
        self.model_adapter = model_adapter or ModelAdapter.from_env()

    def is_configured(self) -> bool:
        return self.model_adapter.is_configured()

    def _build_request(
        self,
        audit_context: Dict[str, Any],
        audit_plan: Dict[str, Any],
        retrieved_chunks: List[Dict[str, Any]],
        model_name: Optional[str] = None,
    ) -> ModelRequest:
        messages = build_reasoning_messages(
            audit_context=audit_context,
            audit_plan=audit_plan,
            retrieved_chunks=retrieved_chunks[:3],
            output_schema_template=None,
        )
        return ModelRequest(
            task_type="reasoning",
            messages=messages,
            model_name=model_name or "gpt-4.1-mini",
            temperature=None,
            max_output_tokens=1800,
            reasoning_effort=None,
            metadata={
                "audit_type": audit_context.get("audit_type"),
                "industry": audit_context.get("industry"),
                "jurisdiction_count": len(audit_context.get("jurisdictions", [])),
                "retrieved_chunk_count": len(retrieved_chunks[:3]),
                "mode": "overlay_only",
            },
        )

    def reason(
        self,
        audit_context: Dict[str, Any],
        audit_plan: Dict[str, Any],
        retrieved_chunks: List[Dict[str, Any]],
        model_name: Optional[str] = None,
    ) -> ModelReasonerResult:
        if model_name == "gpt-5-nano":
            raise ModelReasonerError("gpt-5-nano is not allowed for full audit reasoning overlay; use gpt-5-mini")

        request = self._build_request(
            audit_context=audit_context,
            audit_plan=audit_plan,
            retrieved_chunks=retrieved_chunks,
            model_name=model_name,
        )

        try:
            model_response = self.model_adapter.generate_json(request)
        except ModelAdapterError as exc:
            raise ModelReasonerError(f"Model reasoner failed during model call: {exc}") from exc

        shell = _empty_overlay_shell(audit_context, audit_plan, retrieved_chunks)
        repair_result = repair_to_template(model_response.content, shell)
        repaired_output = repair_result.repaired_output

        exact_errors = validate_exact_shape(repaired_output, shell)
        all_errors = list(repair_result.errors) + list(exact_errors)

        if exact_errors:
            raise ModelReasonerError(
                "Model overlay could not be repaired into overlay schema: " + " | ".join(exact_errors[:20])
            )

        return ModelReasonerResult(
            output=repaired_output,
            model_name=model_response.model_name,
            provider=model_response.provider,
            repaired=not repair_result.is_valid,
            validation_errors=all_errors,
            model_metadata=request.metadata,
        )
