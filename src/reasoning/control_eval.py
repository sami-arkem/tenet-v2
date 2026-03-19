from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.core.library_loader import load_control_library as load_control_library_v2


def load_control_library() -> List[Dict[str, Any]]:
    raw_controls = list(load_control_library_v2().get("controls", []))
    normalized: List[Dict[str, Any]] = []
    for control in raw_controls:
        required_evidence = list(control.get("required_evidence", []))
        normalized.append(
            {
                "control_id": control.get("control_id", ""),
                "title": control.get("control_name", ""),
                "domain": control.get("category", ""),
                "severity_if_missing": control.get("severity_if_missing", "low"),
                "required_evidence": required_evidence,
                # Reuse required evidence terms as deterministic matching anchors.
                "expected_artifacts": required_evidence,
                "keywords": [
                    control.get("control_name", ""),
                    control.get("category", ""),
                    control.get("description", ""),
                    control.get("risk_if_missing", ""),
                    *required_evidence,
                ],
            }
        )
    return normalized


def index_controls_by_id(controls: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {c["control_id"]: c for c in controls}


def _normalize_text(value: str) -> str:
    return (value or "").strip().lower()


def _chunk_text(chunk: Dict[str, Any]) -> str:
    fields = [
        chunk.get("text", ""),
        chunk.get("document_name", ""),
        chunk.get("source_name", ""),
        chunk.get("audit_domain", ""),
        chunk.get("jurisdiction", ""),
        chunk.get("industry", ""),
    ]
    return " ".join(_normalize_text(v) for v in fields if isinstance(v, str))


def _score_control_against_chunk(control: Dict[str, Any], chunk: Dict[str, Any]) -> int:
    haystack = _chunk_text(chunk)
    score = 0

    for kw in control.get("keywords", []):
        if _normalize_text(kw) in haystack:
            score += 2

    for artifact in control.get("expected_artifacts", []):
        if _normalize_text(artifact) in haystack:
            score += 3

    if _normalize_text(control.get("domain", "")) in haystack:
        score += 1

    return score


def evaluate_control(control: Dict[str, Any], retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    ranked: List[Tuple[int, Dict[str, Any]]] = []
    for chunk in retrieved_chunks:
        score = _score_control_against_chunk(control, chunk)
        if score > 0:
            ranked.append((score, chunk))

    ranked.sort(key=lambda x: x[0], reverse=True)
    matched = ranked[:5]

    matched_chunk_ids = [c.get("chunk_id") for _, c in matched if c.get("chunk_id")]
    citations = [
        {
            "chunk_id": c.get("chunk_id"),
            "document_name": c.get("document_name"),
            "source_name": c.get("source_name"),
            "url": c.get("url"),
        }
        for _, c in matched
    ]

    best_score = matched[0][0] if matched else 0

    if best_score >= 8:
        status = "met"
        evidence_status = "sufficient"
        confidence = 0.85
    elif best_score >= 4:
        status = "partial"
        evidence_status = "partial"
        confidence = 0.65
    elif best_score > 0:
        status = "unknown"
        evidence_status = "partial"
        confidence = 0.40
    else:
        status = "missing"
        evidence_status = "missing"
        confidence = 0.20

    rationale = (
        f"Control {control['control_id']} evaluated using keyword and artifact matching "
        f"over retrieved evidence. Best score={best_score}, matched_chunks={len(matched_chunk_ids)}."
    )

    return {
        "control_id": control["control_id"],
        "title": control["title"],
        "domain": control["domain"],
        "severity_if_missing": control["severity_if_missing"],
        "status": status,
        "evidence_status": evidence_status,
        "confidence": confidence,
        "rationale": rationale,
        "matched_chunk_ids": matched_chunk_ids,
        "citations": citations,
    }


def evaluate_controls(required_control_ids: List[str], retrieved_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    controls = load_control_library()
    controls_by_id = index_controls_by_id(controls)

    results: List[Dict[str, Any]] = []
    for control_id in required_control_ids:
        control = controls_by_id[control_id]
        results.append(evaluate_control(control, retrieved_chunks))

    return results


def summarize_gaps(control_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    missing_controls = []
    missing_evidence = []

    for result in control_results:
        if result["status"] in {"missing", "partial", "unknown"}:
            missing_controls.append(
                {
                    "control_id": result["control_id"],
                    "title": result["title"],
                    "domain": result["domain"],
                    "severity": result["severity_if_missing"],
                    "rationale": result["rationale"],
                }
            )
        if result["evidence_status"] in {"missing", "partial"}:
            missing_evidence.append(
                {
                    "control_id": result["control_id"],
                    "title": result["title"],
                    "needed_evidence_status": result["evidence_status"],
                    "rationale": result["rationale"],
                }
            )

    return {
        "missing_controls": missing_controls,
        "missing_evidence": missing_evidence,
    }
