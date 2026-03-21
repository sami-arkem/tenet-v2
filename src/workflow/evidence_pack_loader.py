from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class EvidencePackError(RuntimeError):
    pass


REQUIRED_AUDIT_CONTEXT_FIELDS = {
    "audit_id",
    "entity_name",
    "audit_type",
    "industry",
    "jurisdictions",
    "source_families",
    "query_terms",
    "top_k",
}


def load_evidence_pack(pack_dir: str | Path) -> Dict[str, Any]:
    pack_path = Path(pack_dir)
    if not pack_path.exists() or not pack_path.is_dir():
        raise EvidencePackError(f"Evidence pack directory not found: {pack_path}")

    audit_context_path = pack_path / "audit_context.json"
    if not audit_context_path.exists():
        raise EvidencePackError(f"Missing audit_context.json in {pack_path}")

    audit_context = json.loads(audit_context_path.read_text(encoding="utf-8"))
    missing = sorted(REQUIRED_AUDIT_CONTEXT_FIELDS - set(audit_context.keys()))
    if missing:
        raise EvidencePackError(f"Missing required audit_context fields: {missing}")

    notes_path = pack_path / "notes.md"
    source_inventory_path = pack_path / "source_inventory.json"

    return {
        "pack_dir": pack_path,
        "audit_context": audit_context,
        "notes_path": notes_path if notes_path.exists() else None,
        "source_inventory_path": source_inventory_path if source_inventory_path.exists() else None,
    }
