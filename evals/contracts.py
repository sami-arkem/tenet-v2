from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class EvalAssertionSet:
    equals: Dict[str, Any] = field(default_factory=dict)
    contains: Dict[str, List[Any]] = field(default_factory=dict)
    minimums: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    case_dir: Path
    audit_context: Dict[str, Any]
    assertions: EvalAssertionSet
    case_notes: str


@dataclass(frozen=True)
class EvalResult:
    case_id: str
    passed: bool
    score: float
    max_score: float
    weighted_score: float
    threshold: float
    failures: List[str]
    output: Dict[str, Any]
