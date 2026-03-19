from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from src.intake.contracts import NormalizedAuditContext


REQUIRED_FIELDS = ["audit_type", "industry", "jurisdictions"]


@dataclass
class IntakeState:
    context: NormalizedAuditContext = field(default_factory=NormalizedAuditContext)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    asked_questions: List[str] = field(default_factory=list)
    inferred_facts: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    ready_for_reasoning: bool = False

    def missing_required_fields(self) -> List[str]:
        missing: List[str] = []
        if not self.context.audit_type:
            missing.append("audit_type")
        if not self.context.industry:
            missing.append("industry")
        if not self.context.jurisdictions:
            missing.append("jurisdictions")
        return missing

    def known_summary(self) -> Dict[str, object]:
        return {
            "audit_type": self.context.audit_type,
            "industry": self.context.industry,
            "jurisdictions": self.context.jurisdictions,
            "entity_name": self.context.entity_name,
            "entity_type": self.context.entity_type,
            "products": self.context.products,
            "customer_types": self.context.customer_types,
            "evidence_paths": self.context.evidence_paths,
        }

    def update_ready_flag(self) -> None:
        self.ready_for_reasoning = len(self.missing_required_fields()) == 0
