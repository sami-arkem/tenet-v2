from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


DECISION_POLICY_PATH = Path("data/config/decision_policy_v1.json")


def load_decision_policy(path: Path = DECISION_POLICY_PATH) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def decide_deployment(control_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    policy = load_decision_policy()

    critical_missing = sum(
        1 for r in control_results
        if r.get("severity_if_missing") == "critical" and r.get("status") == "missing"
    )
    high_missing = sum(
        1 for r in control_results
        if r.get("severity_if_missing") == "high" and r.get("status") == "missing"
    )
    avg_confidence = (
        sum(float(r.get("confidence", 0.0)) for r in control_results) / len(control_results)
        if control_results else 0.0
    )

    if (
        critical_missing >= policy["blocked"]["critical_missing_controls_gte"]
        or high_missing >= policy["blocked"]["high_missing_controls_gte"]
        or avg_confidence < policy["blocked"]["min_confidence_override"]
    ):
        return {
            "decision": "BLOCKED",
            "critical_missing_controls": critical_missing,
            "high_missing_controls": high_missing,
            "average_confidence": round(avg_confidence, 3),
            "rationale": "Deployment blocked due to missing critical/high-severity controls or insufficient confidence."
        }

    if (
        critical_missing <= policy["approved"]["max_critical_missing_controls"]
        and high_missing <= policy["approved"]["max_high_missing_controls"]
        and avg_confidence >= policy["approved"]["min_confidence"]
    ):
        return {
            "decision": "APPROVED",
            "critical_missing_controls": critical_missing,
            "high_missing_controls": high_missing,
            "average_confidence": round(avg_confidence, 3),
            "rationale": "Deployment approved because required controls appear materially sufficient with strong confidence."
        }

    return {
        "decision": "CONDITIONALLY_APPROVED",
        "critical_missing_controls": critical_missing,
        "high_missing_controls": high_missing,
        "average_confidence": round(avg_confidence, 3),
        "rationale": "Deployment conditionally approved because remediation or additional evidence is still required."
    }
