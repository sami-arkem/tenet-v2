from __future__ import annotations

from typing import Dict, Optional

from src.intake.normalize import normalize_state_to_audit_context, normalize_turn
from src.intake.prompt_builder import build_intake_messages
from src.intake.question_selector import select_next_question
from src.intake.state import IntakeState
from src.intake.contracts import IntakeTurn
from src.llm.openai_compatible import OpenAICompatibleClient


REQUIRED_MODEL_KEYS = {
    "assistant_opening",
    "understanding_summary",
    "confidence_line",
    "next_question",
    "why_this_matters",
    "question_key_guess",
}


def _fallback_response(state: IntakeState) -> Dict[str, object]:
    next_question = select_next_question(state)
    opening = "Understood. I’m tightening the audit picture."
    summary = "Current read: " + str(state.known_summary())
    confidence = (
        "Core audit context is now complete enough to start reasoning."
        if state.ready_for_reasoning
        else "Still needed before reasoning: " + ", ".join(state.missing_required_fields())
    )

    parts = [opening, summary, confidence]
    if next_question:
        state.asked_questions.append(next_question.key)
        parts.append(f"Next question: {next_question.prompt}")
        parts.append(f"Why this matters: {next_question.reason}")
    else:
        parts.append("I have enough to hand this into the reasoning engine.")

    assistant_message = "\n".join(parts)
    state.conversation_history.append({"role": "assistant", "content": assistant_message})

    return {
        "assistant_message": assistant_message,
        "state": state,
        "normalized_audit_context": normalize_state_to_audit_context(state),
        "ready_for_reasoning": state.ready_for_reasoning,
        "next_question_key": next_question.key if next_question else None,
        "response_source": "deterministic_fallback",
    }


def _validate_model_payload(payload: Dict[str, object]) -> bool:
    if not isinstance(payload, dict):
        return False
    if not REQUIRED_MODEL_KEYS.issubset(payload.keys()):
        return False
    return all(isinstance(payload[k], str) for k in REQUIRED_MODEL_KEYS)


def orchestrate_ai_intake_turn(
    state: IntakeState,
    user_message: str,
    uploaded_filenames: Optional[list[str]] = None,
    uploaded_urls: Optional[list[str]] = None,
    client: Optional[OpenAICompatibleClient] = None,
) -> Dict[str, object]:
    turn = IntakeTurn(
        user_message=user_message,
        uploaded_filenames=uploaded_filenames or [],
        uploaded_urls=uploaded_urls or [],
    )
    state = normalize_turn(state, turn)

    client = client or OpenAICompatibleClient()
    if not client.is_configured():
        return _fallback_response(state)

    try:
        payload = client.chat_json(build_intake_messages(state))
        if not _validate_model_payload(payload):
            return _fallback_response(state)

        next_question_key = payload.get("question_key_guess") or None
        if isinstance(next_question_key, str) and next_question_key:
            state.asked_questions.append(next_question_key)

        assistant_message = "\n".join([
            payload["assistant_opening"].strip(),
            payload["understanding_summary"].strip(),
            payload["confidence_line"].strip(),
            f"Next question: {payload['next_question'].strip()}",
            f"Why this matters: {payload['why_this_matters'].strip()}",
        ])

        state.conversation_history.append({"role": "assistant", "content": assistant_message})

        return {
            "assistant_message": assistant_message,
            "state": state,
            "normalized_audit_context": normalize_state_to_audit_context(state),
            "ready_for_reasoning": state.ready_for_reasoning,
            "next_question_key": next_question_key,
            "response_source": "ai_orchestrator",
        }
    except Exception:
        return _fallback_response(state)
