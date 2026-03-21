from src.reasoning.prompt_builder import (
    build_reasoning_messages,
    build_retrieval_followup_messages,
)


def test_build_reasoning_messages_returns_two_messages():
    messages = build_reasoning_messages(
        audit_context={"audit_type": "aml_readiness_review", "industry": "fintech", "jurisdictions": ["US"]},
        audit_plan={"applicable_regimes": ["BSA_AML"], "required_control_ids": ["AML-001"]},
        retrieved_chunks=[
            {
                "chunk_id": "c1",
                "document_name": "AML Policy",
                "source_name": "policy_repo",
                "text": "This policy defines AML governance and escalation.",
            }
        ],
    )
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_build_retrieval_followup_messages_returns_two_messages():
    messages = build_retrieval_followup_messages(
        known_context={"audit_type": "aml_readiness_review", "industry": "fintech"},
        retrieved_chunks=[
            {
                "chunk_id": "c1",
                "document_name": "AML Policy",
                "text": "Transaction monitoring is referenced but scope is unclear.",
            }
        ],
        missing_fields=["entity_name"],
    )
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
