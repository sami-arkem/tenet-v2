from __future__ import annotations

import json
from pathlib import Path
from typing import List

from evals.contracts import EvalAssertionSet, EvalCase


def _read_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def load_eval_cases(base_dir: str | Path = "evals/gold_cases") -> List[EvalCase]:
    root = Path(base_dir)
    if not root.exists():
        raise FileNotFoundError(f"Gold case directory not found: {root}")

    cases: List[EvalCase] = []
    for case_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        audit_context = _read_json(case_dir / "audit_context.json")
        expected = _read_json(case_dir / "expected_assertions.json")
        case_notes = _read_text(case_dir / "case_notes.md")

        case_id = expected.get("case_id") or case_dir.name
        assertions = expected.get("expected", {})
        case = EvalCase(
            case_id=case_id,
            case_dir=case_dir,
            audit_context=audit_context,
            assertions=EvalAssertionSet(
                equals=assertions.get("equals", {}),
                contains=assertions.get("contains", {}),
                minimums=assertions.get("minimums", {}),
            ),
            case_notes=case_notes,
        )
        cases.append(case)

    return cases
