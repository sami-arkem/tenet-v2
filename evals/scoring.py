from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_eval_policy(path: str | Path = "data/config/eval_policy_v1.json") -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Eval policy not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_path_value(obj: Any, path: str) -> Any:
    current = obj
    parts = path.split(".")
    for part in parts:
        if isinstance(current, dict):
            if part not in current:
                raise KeyError(f"Missing path segment '{part}' in path '{path}'")
            current = current[part]
        elif isinstance(current, list):
            extracted = []
            for item in current:
                if isinstance(item, dict) and part in item:
                    extracted.append(item[part])
            current = extracted
        else:
            raise KeyError(f"Cannot traverse path '{path}' through value of type {type(current).__name__}")
    return current


def _normalize_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return [value]


def score_equals(output: Dict[str, Any], expected: Dict[str, Any]) -> Tuple[float, float, List[str]]:
    earned = 0.0
    total = float(len(expected))
    failures: List[str] = []

    if total == 0:
        return 0.0, 0.0, failures

    for path, exp_value in expected.items():
        try:
            actual = get_path_value(output, path)
        except KeyError as exc:
            failures.append(f"{path}: missing path ({exc})")
            continue

        if actual == exp_value:
            earned += 1.0
        else:
            failures.append(f"{path}: expected exact {exp_value!r}, got {actual!r}")

    return earned, total, failures


def score_contains(output: Dict[str, Any], expected: Dict[str, List[Any]]) -> Tuple[float, float, List[str]]:
    earned = 0.0
    total = float(len(expected))
    failures: List[str] = []

    if total == 0:
        return 0.0, 0.0, failures

    for path, exp_values in expected.items():
        try:
            actual = get_path_value(output, path)
        except KeyError as exc:
            failures.append(f"{path}: missing path ({exc})")
            continue

        actual_list = _normalize_list(actual)
        missing = [v for v in exp_values if v not in actual_list]
        if not missing:
            earned += 1.0
        else:
            failures.append(f"{path}: missing expected values {missing!r}; actual={actual_list!r}")

    return earned, total, failures


def score_minimums(output: Dict[str, Any], expected: Dict[str, float]) -> Tuple[float, float, List[str]]:
    earned = 0.0
    total = float(len(expected))
    failures: List[str] = []

    if total == 0:
        return 0.0, 0.0, failures

    for path, minimum in expected.items():
        try:
            actual = get_path_value(output, path)
        except KeyError as exc:
            failures.append(f"{path}: missing path ({exc})")
            continue

        if not isinstance(actual, (int, float)):
            failures.append(f"{path}: expected numeric actual value, got {type(actual).__name__}")
            continue

        if float(actual) >= float(minimum):
            earned += 1.0
        else:
            failures.append(f"{path}: expected >= {minimum}, got {actual}")

    return earned, total, failures


def weighted_score(output: Dict[str, Any], assertions: Dict[str, Any], policy: Dict[str, Any]) -> Tuple[float, float, List[str]]:
    weights = policy.get("scoring_weights", {})
    failures: List[str] = []
    earned_total = 0.0
    possible_total = 0.0

    equals = assertions.get("equals", {})
    contains = assertions.get("contains", {})
    minimums = assertions.get("minimums", {})

    for path, expected in equals.items():
        weight = float(weights.get(path, 0.0))
        possible_total += weight
        try:
            actual = get_path_value(output, path)
            if actual == expected:
                earned_total += weight
            else:
                failures.append(f"{path}: expected exact {expected!r}, got {actual!r}")
        except KeyError as exc:
            failures.append(f"{path}: missing path ({exc})")

    for path, expected_values in contains.items():
        weight = float(weights.get(path, 0.0))
        possible_total += weight
        try:
            actual = get_path_value(output, path)
            actual_list = _normalize_list(actual)
            missing = [v for v in expected_values if v not in actual_list]
            if not missing:
                earned_total += weight
            else:
                failures.append(f"{path}: missing expected values {missing!r}; actual={actual_list!r}")
        except KeyError as exc:
            failures.append(f"{path}: missing path ({exc})")

    for path, minimum in minimums.items():
        weight = float(weights.get(path, 0.0))
        possible_total += weight
        try:
            actual = get_path_value(output, path)
            if isinstance(actual, (int, float)) and float(actual) >= float(minimum):
                earned_total += weight
            else:
                failures.append(f"{path}: expected >= {minimum}, got {actual!r}")
        except KeyError as exc:
            failures.append(f"{path}: missing path ({exc})")

    return earned_total, possible_total, failures
