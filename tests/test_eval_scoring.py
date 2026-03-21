from evals.scoring import score_contains, score_equals, score_minimums, weighted_score


def test_eval_scoring_functions():
    output = {
        "deployment_decision": {"status": "BLOCKED"},
        "regulatory_applicability": {"primary_regimes": ["BSA_AML", "UK_MLR"]},
        "control_assessment": {"control_coverage_score": 47},
        "missing_controls": [{"control_id": "AML-003"}],
        "missing_evidence": [{"title": "TM policy"}],
        "findings": [{"title": "Transaction monitoring framework documented"}]
    }

    eq = {"deployment_decision.status": "BLOCKED"}
    ct = {
        "regulatory_applicability.primary_regimes": ["BSA_AML"],
        "missing_controls.control_id": ["AML-003"],
        "missing_evidence.title": ["TM policy"],
        "findings.title": ["Transaction monitoring framework documented"]
    }
    mn = {"control_assessment.control_coverage_score": 40}

    eq_earned, eq_total, _ = score_equals(output, eq)
    ct_earned, ct_total, _ = score_contains(output, ct)
    mn_earned, mn_total, _ = score_minimums(output, mn)

    assert eq_earned == eq_total == 1.0
    assert ct_earned == ct_total == 4.0
    assert mn_earned == mn_total == 1.0

    weighted, possible, failures = weighted_score(
        output,
        {"equals": eq, "contains": ct, "minimums": mn},
        {
            "scoring_weights": {
                "deployment_decision.status": 0.30,
                "regulatory_applicability.primary_regimes": 0.20,
                "missing_controls.control_id": 0.20,
                "missing_evidence.title": 0.15,
                "findings.title": 0.15,
                "control_assessment.control_coverage_score": 0.10
            }
        },
    )
    assert weighted > 0
    assert possible > 0
    assert failures == []
