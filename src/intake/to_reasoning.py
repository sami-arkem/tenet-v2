from __future__ import annotations

from typing import Dict

from src.core.contracts import validate_audit_context
from src.intake.normalize import normalize_state_to_audit_context
from src.intake.state import IntakeState
from src.reasoning.reason import reason


def run_reasoning_from_intake_state(state: IntakeState) -> Dict[str, object]:
    audit_context = normalize_state_to_audit_context(state)
    errors = validate_audit_context(audit_context)
    if errors:
        raise ValueError("Cannot run reasoning from intake state: " + " | ".join(errors))
    return reason(audit_context)
