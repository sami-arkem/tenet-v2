from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


JURISDICTION_PACKS_ROOT = Path("data/packs/jurisdictions")
DOMAIN_PACKS_ROOT = Path("data/packs/domains")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing pack file: {path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid pack JSON: {path}") from exc


def _load_packs(root: Path) -> Dict[str, Dict[str, Any]]:
    packs: Dict[str, Dict[str, Any]] = {}
    if not root.exists():
        return packs
    for pack_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        pack_file = pack_dir / "pack.json"
        if pack_file.exists():
            data = _read_json(pack_file)
            key = data.get("jurisdiction") or data.get("domain") or pack_dir.name
            packs[str(key)] = data
    return packs


def load_jurisdiction_packs() -> Dict[str, Dict[str, Any]]:
    return _load_packs(JURISDICTION_PACKS_ROOT)


def load_domain_packs() -> Dict[str, Dict[str, Any]]:
    return _load_packs(DOMAIN_PACKS_ROOT)


def supported_domains_for_jurisdiction(jurisdiction: str) -> List[str]:
    packs = load_jurisdiction_packs()
    return list(packs.get(jurisdiction, {}).get("supported_domains", []))


def control_ids_for_domain(domain: str) -> List[str]:
    packs = load_domain_packs()
    return list(packs.get(domain, {}).get("control_ids", []))


def query_seeds_for_domain(domain: str) -> List[str]:
    packs = load_domain_packs()
    return list(packs.get(domain, {}).get("query_seeds", []))


def composed_control_ids(domains: List[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for domain in domains:
        for control_id in control_ids_for_domain(domain):
            if control_id not in seen:
                seen.add(control_id)
                result.append(control_id)
    return result
