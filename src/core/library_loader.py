from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


CONTROL_LIBRARY_PATH = Path("data/config/control_library_v2.json")
REGIME_LIBRARY_PATH = Path("data/config/regime_library_v2.json")
AUDIT_TYPE_CONTROL_MAP_PATH = Path("data/config/audit_type_control_map_v2.json")
AUDIT_TYPE_REGIME_MAP_PATH = Path("data/config/audit_type_regime_map_v2.json")


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_control_library() -> Dict[str, Any]:
    return _load_json(CONTROL_LIBRARY_PATH)


def load_regime_library() -> Dict[str, Any]:
    return _load_json(REGIME_LIBRARY_PATH)


def load_audit_type_control_map() -> Dict[str, List[str]]:
    return _load_json(AUDIT_TYPE_CONTROL_MAP_PATH)


def load_audit_type_regime_map() -> Dict[str, Dict[str, List[str]]]:
    return _load_json(AUDIT_TYPE_REGIME_MAP_PATH)


def control_ids_for_audit_type(audit_type: str) -> List[str]:
    mapping = load_audit_type_control_map()
    return list(mapping.get(audit_type, []))


def regime_ids_for_audit_type_and_jurisdictions(audit_type: str, jurisdictions: List[str]) -> List[str]:
    mapping = load_audit_type_regime_map()
    audit_map = mapping.get(audit_type, {})
    result: List[str] = []
    for jurisdiction in jurisdictions:
        result.extend(audit_map.get(jurisdiction, []))
    seen = set()
    ordered = []
    for item in result:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered
