from __future__ import annotations

from dataclasses import dataclass
from typing import List

from src.intake.state import IntakeState


@dataclass
class SelectedQuestion:
    key: str
    prompt: str
    reason: str
    priority: int


QUESTION_BANK = {
    "audit_type": SelectedQuestion(
        key="audit_type",
        prompt="What should I evaluate first: AML readiness, KYC/KYB controls, sanctions readiness, governance gaps, or vendor compliance readiness?",
        reason="This sets the audit lane before I start behaving like an overcaffeinated control matrix.",
        priority=100,
    ),
    "industry": SelectedQuestion(
        key="industry",
        prompt="Which best describes you today: fintech, payments, or crypto?",
        reason="Industry changes the control baseline fast.",
        priority=95,
    ),
    "jurisdictions": SelectedQuestion(
        key="jurisdictions",
        prompt="Which jurisdictions matter for this review right now? For MVP I can anchor to US, UK, and EU.",
        reason="Jurisdiction drives regime selection and evidence expectations.",
        priority=90,
    ),
    "entity_name": SelectedQuestion(
        key="entity_name",
        prompt="What is the legal or operating name of the entity under review?",
        reason="I use this to keep the audit context grounded and report-ready.",
        priority=70,
    ),
    "entity_type": SelectedQuestion(
        key="entity_type",
        prompt="How would you describe the entity: payments platform, wallet provider, exchange, issuer, vendor, or something adjacent?",
        reason="Entity type changes which controls I expect to see.",
        priority=68,
    ),
    "products": SelectedQuestion(
        key="products",
        prompt="What products or flows are in scope: wallets, card issuing, merchant acquiring, payouts, cross-border payments, crypto rails?",
        reason="Product surface tells me where the real compliance heat lives.",
        priority=65,
    ),
    "customer_types": SelectedQuestion(
        key="customer_types",
        prompt="Who are your customers in scope: consumers, SMBs, enterprises, merchants, institutional clients?",
        reason="Customer type affects KYC, KYB, beneficial ownership, and monitoring expectations.",
        priority=60,
    ),
    "evidence_paths": SelectedQuestion(
        key="evidence_paths",
        prompt="Do you already have policies, procedures, risk assessments, vendor docs, or screenshots I should treat as evidence?",
        reason="If docs already exist, I can stop guessing and start auditing.",
        priority=55,
    ),
}


def _is_missing(state: IntakeState, key: str) -> bool:
    value = getattr(state.context, key)
    if value is None:
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def select_next_question(state: IntakeState) -> SelectedQuestion | None:
    candidates: List[SelectedQuestion] = []

    for key, question in QUESTION_BANK.items():
        if _is_missing(state, key) and key not in state.asked_questions:
            candidates.append(question)

    if not candidates:
        return None

    candidates.sort(key=lambda q: q.priority, reverse=True)
    return candidates[0]
