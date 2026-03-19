from src.intake.contracts import IntakeTurn
from src.intake.normalize import normalize_turn, normalize_state_to_audit_context
from src.intake.state import IntakeState


def test_normalize_turn_extracts_core_fields():
    state = IntakeState()
    turn = IntakeTurn(
        user_message="We are a fintech payments platform in the US and UK doing AML readiness review for SMB onboarding and cross border payments."
    )
    state = normalize_turn(state, turn)
    obj = normalize_state_to_audit_context(state)

    assert obj["audit_type"] == "aml_readiness_review"
    assert obj["industry"] in {"fintech", "payments"}
    assert "US" in obj["jurisdictions"]
    assert "UK" in obj["jurisdictions"]
    assert state.ready_for_reasoning is True
