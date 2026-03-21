from src.intake.orchestrator import orchestrate_intake_turn
from src.intake.to_reasoning import run_reasoning_from_intake_state
from src.intake.state import IntakeState


def test_run_reasoning_from_intake_state():
    state = IntakeState()
    orchestrate_intake_turn(
        state,
        "We are a fintech payments platform in the US and UK and want an AML readiness review."
    )
    result = run_reasoning_from_intake_state(state)
    assert "deployment_decision" in result
    assert "control_assessment" in result
