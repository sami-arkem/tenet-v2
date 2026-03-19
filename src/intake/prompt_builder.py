from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from src.intake.state import IntakeState


QUESTION_POLICY_PATH = Path("data/config/intake_question_policy_v1.json")


def load_question_policy() -> Dict[str, object]:
    with QUESTION_POLICY_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _known_context_snapshot(state: IntakeState) -> Dict[str, object]:
    return {
        "audit_type": state.context.audit_type,
        "industry": state.context.industry,
        "jurisdictions": state.context.jurisdictions,
        "entity_name": state.context.entity_name,
        "entity_type": state.context.entity_type,
        "products": state.context.products,
        "customer_types": state.context.customer_types,
        "distribution_channels": state.context.distribution_channels,
        "payment_flows": state.context.payment_flows,
        "data_categories_processed": state.context.data_categories_processed,
        "high_risk_activities": state.context.high_risk_activities,
        "evidence_paths": state.context.evidence_paths,
        "field_confidence": state.context.field_confidence,
        "missing_required_fields": state.missing_required_fields(),
        "ready_for_reasoning": state.ready_for_reasoning,
    }


def build_intake_messages(state: IntakeState) -> List[Dict[str, str]]:
    policy = load_question_policy()
    snapshot = _known_context_snapshot(state)
    history = state.conversation_history[-8:]

    system = f"""
You are Tenet, an elite AI compliance strategist running audit intake.
Your job is to ask the single next best question.

Rules:
{json.dumps(policy["system_rules"], indent=2)}

Style:
{json.dumps(policy["style_rules"], indent=2)}

Return JSON only with keys:
assistant_opening
understanding_summary
confidence_line
next_question
why_this_matters
question_key_guess

Constraints:
- Never sound like a form.
- Never ask for information already clearly known.
- Keep the next_question to one question only.
- Keep humor light, dry, premium, and sparse.
- If enough information exists to begin reasoning, say so.
- Ground everything in the provided intake state.
""".strip()

    user = {
        "known_context": snapshot,
        "recent_history": history,
        "instruction": "Generate the next best assistant response for intake."
    }

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]
