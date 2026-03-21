from src.intake.orchestrator import orchestrate_intake_turn
from src.intake.state import IntakeState


def test_orchestrator_asks_next_best_question():
    state = IntakeState()
    result = orchestrate_intake_turn(
        state,
        "We are a crypto exchange in the EU and UK and want a sanctions review."
    )
    assert "assistant_message" in result
    assert result["next_question_key"] is not None


def test_orchestrator_can_become_reasoning_ready():
    state = IntakeState()
    result = orchestrate_intake_turn(
        state,
        "We are a fintech payment platform in the US and UK and want an AML readiness review."
    )
    assert result["ready_for_reasoning"] is True
