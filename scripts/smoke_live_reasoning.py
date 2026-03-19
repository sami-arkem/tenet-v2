import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.reasoning.model_reasoner import ModelReasoner
from src.reasoning.reason import reason

result = reason(
    {
        "audit_id": "live-check-001",
        "entity_name": "Live Check Entity",
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US"],
        "source_families": ["regulations", "aml"],
        "query_terms": ["aml policy", "transaction monitoring"],
        "top_k": 2,
        "reasoning_model_name": "gpt-4.1-mini"
    },
    reasoner=ModelReasoner(),
    runtime_config={
        "enable_model_reasoning": True,
        "model_overlay_sections": [
            "executive_summary",
            "reporting_outputs"
        ],
        "fallback_to_deterministic_on_model_error": False,
        "require_retrieved_chunks_for_model_reasoning": True
    }
)

print("reasoning_mode:", result["audit_meta"]["reasoning_mode"])
print("model_version:", result["audit_meta"]["model_version"])
print("decision:", result["deployment_decision"]["status"])
