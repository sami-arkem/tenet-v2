from src.intake.prompt_builder import build_intake_messages
from src.intake.state import IntakeState


def test_build_intake_messages_returns_chat_messages():
    state = IntakeState()
    messages = build_intake_messages(state)
    assert isinstance(messages, list)
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
