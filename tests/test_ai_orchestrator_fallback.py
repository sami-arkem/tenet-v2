from src.intake.ai_orchestrator import orchestrate_ai_intake_turn
from src.intake.state import IntakeState


def test_ai_orchestrator_falls_back_without_model_config():
    state = IntakeState()
    result = orchestrate_ai_intake_turn(
        state,
        "We are a fintech payments platform in the US and UK and want an AML readiness review."
    )
    assert result["response_source"] == "deterministic_fallback"
    assert "assistant_message" in result
