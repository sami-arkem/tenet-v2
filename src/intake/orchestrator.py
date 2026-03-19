from __future__ import annotations

from typing import Dict, Optional

from src.intake.contracts import IntakeTurn
from src.intake.normalize import normalize_state_to_audit_context, normalize_turn
from src.intake.question_selector import select_next_question
from src.intake.state import IntakeState


def _summary_line(state: IntakeState) -> str:
    ctx = state.context
    bits = []
    if ctx.entity_name:
        bits.append(ctx.entity_name)
    if ctx.industry:
        bits.append(ctx.industry)
    if ctx.jurisdictions:
        bits.append("/".join(ctx.jurisdictions))
    if ctx.audit_type:
        bits.append(ctx.audit_type.replace("_", " "))
    if not bits:
        return "I am still forming the picture."
    return "Current read: " + " | ".join(bits)


def _confidence_line(state: IntakeState) -> str:
    missing = state.missing_required_fields()
    if not missing:
        return "Core audit context is now complete enough to start reasoning."
    return "Still needed before reasoning: " + ", ".join(missing)


def _opening_feedback(state: IntakeState) -> str:
    ctx = state.context
    if ctx.audit_type and ctx.jurisdictions:
        return "Nice. The scope is starting to look properly auditable rather than spiritually optimistic."
    if ctx.industry or ctx.products:
        return "Good signal. I can already see the control baseline taking shape."
    return "Understood. I am building the audit picture as we go."


def orchestrate_intake_turn(state: IntakeState, user_message: str, uploaded_filenames: Optional[list[str]] = None, uploaded_urls: Optional[list[str]] = None) -> Dict[str, object]:
    turn = IntakeTurn(
        user_message=user_message,
        uploaded_filenames=uploaded_filenames or [],
        uploaded_urls=uploaded_urls or [],
    )

    state = normalize_turn(state, turn)
    next_question = select_next_question(state)
    normalized = normalize_state_to_audit_context(state)

    response_parts = [
        _opening_feedback(state),
        _summary_line(state),
        _confidence_line(state),
    ]

    if next_question:
        state.asked_questions.append(next_question.key)
        response_parts.append(f"Next question: {next_question.prompt}")
        response_parts.append(f"Why this matters: {next_question.reason}")
    else:
        response_parts.append("I have enough to hand this into the reasoning engine.")

    assistant_message = "\n".join(response_parts)

    state.conversation_history.append({"role": "assistant", "content": assistant_message})

    return {
        "assistant_message": assistant_message,
        "state": state,
        "normalized_audit_context": normalized,
        "ready_for_reasoning": state.ready_for_reasoning,
        "next_question_key": next_question.key if next_question else None,
    }
