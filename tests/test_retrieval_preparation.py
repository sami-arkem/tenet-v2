from src.core.retrieval_preparation import build_retrieval_preparation


def test_build_retrieval_preparation():
    prep = build_retrieval_preparation({
        "audit_type": "aml_readiness_review",
        "jurisdictions": ["US"],
        "products": ["wallet"],
        "customer_types": ["consumer"],
        "query_terms": ["transaction monitoring"],
    })
    assert "AML-003" in prep["controls"]
    assert "BSA_AML" in prep["regimes"]
    assert "aml policy" in prep["query_terms"]
    assert "transaction monitoring" in prep["query_terms"]
