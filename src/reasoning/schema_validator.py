from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class SchemaValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    repaired_output: Dict[str, Any] = field(default_factory=dict)


def _typename(value: Any) -> str:
    return type(value).__name__


def _coerce_primitive(value: Any, template: Any) -> Tuple[Any, bool]:
    if template is None:
        return value, True

    if isinstance(template, bool):
        if isinstance(value, bool):
            return value, True
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "yes", "1"}:
                return True, True
            if lowered in {"false", "no", "0"}:
                return False, True
        return template, False

    if isinstance(template, int) and not isinstance(template, bool):
        if isinstance(value, int) and not isinstance(value, bool):
            return value, True
        if isinstance(value, float):
            return int(value), True
        if isinstance(value, str):
            try:
                return int(value.strip()), True
            except Exception:
                return template, False
        return template, False

    if isinstance(template, float):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value), True
        if isinstance(value, str):
            try:
                return float(value.strip()), True
            except Exception:
                return template, False
        return template, False

    if isinstance(template, str):
        if value is None:
            return "", True
        if isinstance(value, str):
            return value, True
        return str(value), True

    return value, isinstance(value, type(template))


def _repair_value(value: Any, template: Any, path: str, errors: List[str]) -> Any:
    if isinstance(template, dict):
        if not isinstance(value, dict):
            errors.append(f"{path}: expected dict, got {_typename(value)}; replaced with template")
            value = {}
        return _repair_dict(value, template, path, errors)

    if isinstance(template, list):
        if not isinstance(value, list):
            errors.append(f"{path}: expected list, got {_typename(value)}; replaced with template")
            return copy.deepcopy(template)

        if len(template) == 0:
            return value

        item_template = template[0]
        repaired_items = []
        for idx, item in enumerate(value):
            repaired_items.append(_repair_value(item, item_template, f"{path}[{idx}]", errors))
        return repaired_items

    repaired, ok = _coerce_primitive(value, template)
    if not ok:
        errors.append(f"{path}: expected {_typename(template)}, got {_typename(value)}; coerced to template-compatible value")
    return repaired


def _repair_dict(value: Dict[str, Any], template: Dict[str, Any], path: str, errors: List[str]) -> Dict[str, Any]:
    repaired: Dict[str, Any] = {}

    for key, tmpl_value in template.items():
        child_path = f"{path}.{key}" if path else key
        if key not in value:
            repaired[key] = copy.deepcopy(tmpl_value)
            errors.append(f"{child_path}: missing key added from template")
            continue
        repaired[key] = _repair_value(value[key], tmpl_value, child_path, errors)

    extra_keys = sorted(set(value.keys()) - set(template.keys()))
    for key in extra_keys:
        child_path = f"{path}.{key}" if path else key
        errors.append(f"{child_path}: unsupported key removed")

    return repaired


def repair_to_template(model_output: Dict[str, Any], schema_template: Dict[str, Any]) -> SchemaValidationResult:
    if not isinstance(model_output, dict):
        return SchemaValidationResult(
            is_valid=False,
            errors=[f"root: expected dict, got {_typename(model_output)}"],
            repaired_output=copy.deepcopy(schema_template),
        )

    errors: List[str] = []
    repaired = _repair_dict(model_output, schema_template, "", errors)
    return SchemaValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        repaired_output=repaired,
    )


def validate_exact_shape(value: Any, template: Any, path: str = "") -> List[str]:
    errors: List[str] = []

    if isinstance(template, dict):
        if not isinstance(value, dict):
            return [f"{path or 'root'}: expected dict, got {_typename(value)}"]

        missing = sorted(set(template.keys()) - set(value.keys()))
        extra = sorted(set(value.keys()) - set(template.keys()))
        for key in missing:
            errors.append(f"{path + '.' if path else ''}{key}: missing")
        for key in extra:
            errors.append(f"{path + '.' if path else ''}{key}: unsupported")

        for key, tmpl_value in template.items():
            if key in value:
                errors.extend(validate_exact_shape(value[key], tmpl_value, f"{path + '.' if path else ''}{key}"))
        return errors

    if isinstance(template, list):
        if not isinstance(value, list):
            return [f"{path or 'root'}: expected list, got {_typename(value)}"]
        if len(template) == 0:
            return []
        item_template = template[0]
        for idx, item in enumerate(value):
            errors.extend(validate_exact_shape(item, item_template, f"{path}[{idx}]"))
        return errors

    if template is None:
        return []

    if isinstance(template, bool):
        if not isinstance(value, bool):
            errors.append(f"{path or 'root'}: expected bool, got {_typename(value)}")
        return errors

    if isinstance(template, int) and not isinstance(template, bool):
        if not (isinstance(value, int) and not isinstance(value, bool)):
            errors.append(f"{path or 'root'}: expected int, got {_typename(value)}")
        return errors

    if isinstance(template, float):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{path or 'root'}: expected float, got {_typename(value)}")
        return errors

    if isinstance(template, str):
        if not isinstance(value, str):
            errors.append(f"{path or 'root'}: expected str, got {_typename(value)}")
        return errors

    return errors
