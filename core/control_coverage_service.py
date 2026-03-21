from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


DEFAULT_AUDIT_ROOT = Path("artifacts") / "audit_runs"


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=False) + "\n")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_audit_detail(run_id: str, audit_root: Path = DEFAULT_AUDIT_ROOT) -> dict[str, Any]:
    run_id = _require_non_empty_str(run_id, "run_id")
    path = audit_root / run_id / "detail.json"
    if not path.exists():
        raise FileNotFoundError(f"audit run not found: {run_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("audit detail must be object")
    return payload


def _coverage_path(run_id: str, audit_root: Path = DEFAULT_AUDIT_ROOT) -> Path:
    run_id = _require_non_empty_str(run_id, "run_id")
    return audit_root / run_id / "control_coverage.json"


def _normalize(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _question_relevant_to_control(question: str, control: dict[str, Any]) -> bool:
    q = _normalize(question)
    control_id = _normalize(str(control.get("control_id", "")))
    title = _normalize(str(control.get("title", "")))
    title_tokens = [x for x in title.split("_") if x]

    if control_id and control_id in q:
        return True

    matched = 0
    for token in title_tokens:
        if len(token) >= 4 and token in q:
            matched += 1
    return matched >= 1


def _collect_context_matches_for_control(
    *,
    context_pack: dict[str, Any],
    control: dict[str, Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in context_pack.get("questions", []):
        if not isinstance(row, dict):
            continue
        question = str(row.get("question", "")).strip()
        if not question or not _question_relevant_to_control(question, control):
            continue
        matches = row.get("matches", [])
        if not isinstance(matches, list):
            continue
        for match in matches:
            if not isinstance(match, dict):
                continue
            out.append(
                {
                    "question": question,
                    "chunk_id": match.get("chunk_id"),
                    "evidence_id": match.get("evidence_id"),
                    "filename": match.get("filename"),
                    "title": match.get("title"),
                    "source_type": match.get("source_type"),
                    "score": match.get("score"),
                    "excerpt": match.get("excerpt"),
                }
            )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in out:
        key = (str(row.get("question")), str(row.get("chunk_id")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _collect_direct_evidence(control_input: dict[str, Any]) -> list[dict[str, Any]]:
    provided = control_input.get("provided_evidence", [])
    if not isinstance(provided, list):
        return []
    out = []
    for row in provided:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "evidence_id": row.get("evidence_id"),
                "title": row.get("title"),
                "source_type": row.get("source_type"),
                "file_path": row.get("file_path"),
                "citation": row.get("citation"),
            }
        )
    return out


def _evaluate_control_coverage(control_input: dict[str, Any], context_pack: dict[str, Any]) -> dict[str, Any]:
    control = control_input.get("control", {})
    if not isinstance(control, dict):
        raise ValueError("control_input.control must be object")

    control_id = _require_non_empty_str(control.get("control_id"), "control.control_id")
    regime_id = _require_non_empty_str(control.get("regime_id"), "control.regime_id")
    title = _require_non_empty_str(control.get("title"), "control.title")

    required_evidence_types = control.get("required_evidence_types", [])
    if not isinstance(required_evidence_types, list):
        raise ValueError("required_evidence_types must be list")
    required_evidence_types = [str(x).strip() for x in required_evidence_types if str(x).strip()]

    direct_evidence = _collect_direct_evidence(control_input)
    direct_types = {
        str(row.get("source_type", "")).strip()
        for row in direct_evidence
        if str(row.get("source_type", "")).strip()
    }

    context_matches = _collect_context_matches_for_control(context_pack=context_pack, control=control)
    context_types = {
        str(row.get("source_type", "")).strip()
        for row in context_matches
        if str(row.get("source_type", "")).strip()
    }

    covered_types = sorted(set(required_evidence_types).intersection(direct_types.union(context_types)))
    missing_required_types = sorted(set(required_evidence_types) - set(covered_types))

    declared_control_present = bool(control_input.get("declared_control_present"))
    declared_operating_effective = control_input.get("declared_operating_effective")

    if declared_control_present is not True:
        coverage_status = "BLOCKED"
        rationale = "Declared control is absent."
    elif missing_required_types:
        coverage_status = "PARTIAL"
        rationale = "Not all required evidence types are covered by direct evidence or retrieved context."
    elif declared_operating_effective is False:
        coverage_status = "PARTIAL"
        rationale = "Required evidence is present, but control is declared not operating effectively."
    else:
        coverage_status = "SUPPORTED"
        rationale = "Required evidence is covered by direct evidence and/or retrieved context."

    return {
        "control_id": control_id,
        "regime_id": regime_id,
        "title": title,
        "coverage_status": coverage_status,
        "declared_control_present": declared_control_present,
        "declared_operating_effective": declared_operating_effective,
        "required_evidence_types": required_evidence_types,
        "covered_evidence_types": covered_types,
        "missing_required_evidence_types": missing_required_types,
        "direct_evidence": direct_evidence,
        "context_matches": context_matches,
        "rationale": rationale,
        "deterministic_authoritative": True,
    }


def build_control_coverage_matrix(
    *,
    run_id: str,
    audit_root: Path = DEFAULT_AUDIT_ROOT,
) -> dict[str, Any]:
    detail = _load_audit_detail(run_id, audit_root)
    deterministic = detail.get("deterministic_audit_result", {})
    if not isinstance(deterministic, dict):
        raise ValueError("deterministic_audit_result must be object")

    scope = deterministic.get("scope", {})
    company = deterministic.get("company_profile", {})
    controls = detail.get("input_payload", {}).get("controls")

    if not isinstance(controls, list):
        controls = []
        evals = deterministic.get("control_evaluations", [])
        if isinstance(evals, list):
            for row in evals:
                if not isinstance(row, dict):
                    continue
                controls.append(
                    {
                        "control": {
                            "control_id": row.get("control_id"),
                            "regime_id": row.get("regime_id"),
                            "title": row.get("control_id"),
                            "required_evidence_types": [],
                        },
                        "provided_evidence": row.get("evidence_refs", []),
                        "declared_control_present": True,
                        "declared_operating_effective": True,
                    }
                )

    context_pack = detail.get("audit_context_pack")
    if not isinstance(context_pack, dict):
        raise ValueError("audit_context_pack must be present for coverage matrix generation")

    rows = [_evaluate_control_coverage(row, context_pack) for row in controls if isinstance(row, dict)]

    supported = sum(1 for row in rows if row["coverage_status"] == "SUPPORTED")
    partial = sum(1 for row in rows if row["coverage_status"] == "PARTIAL")
    blocked = sum(1 for row in rows if row["coverage_status"] == "BLOCKED")

    payload = {
        "run_id": run_id,
        "generated_at": detail.get("created_at"),
        "deterministic_authoritative": True,
        "company_name": company.get("company_name"),
        "audit_type": scope.get("audit_type"),
        "summary": {
            "control_count": len(rows),
            "supported_controls": supported,
            "partial_controls": partial,
            "blocked_controls": blocked,
        },
        "controls": rows,
    }

    _atomic_write_json(_coverage_path(run_id, audit_root), payload)
    return payload


def get_control_coverage_matrix(
    *,
    run_id: str,
    audit_root: Path = DEFAULT_AUDIT_ROOT,
) -> dict[str, Any]:
    path = _coverage_path(run_id, audit_root)
    if not path.exists():
        raise FileNotFoundError(f"control coverage matrix not found for run: {run_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("control coverage matrix must be object")
    return payload
