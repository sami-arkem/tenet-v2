from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_jsonl(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        return []
    rows: List[Dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


class ModelLogPaths:
    def __init__(self, base: str = "state") -> None:
        self.base = base
        self.model_calls = f"{base}/model_calls/model_call_log.jsonl"


def log_model_call(
    *,
    paths: ModelLogPaths,
    tenant_id: str,
    audit_id: str,
    surface: str,
    model_name: str,
    action: str,
    status: str,
    evidence_id: Optional[str] = None,
    input_ref: Optional[str] = None,
    output_ref: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Dict[str, object]:
    rows = _read_jsonl(Path(paths.model_calls))
    now = _now_iso()
    call_id = f"{tenant_id}:{audit_id}:{surface}:{action}:{now}:{len(rows)+1}"
    row = {
        "call_id": call_id,
        "tenant_id": tenant_id,
        "audit_id": audit_id,
        "evidence_id": evidence_id,
        "surface": surface,
        "model_name": model_name,
        "action": action,
        "status": status,
        "input_ref": input_ref,
        "output_ref": output_ref,
        "metadata": metadata or {},
        "created_at": now,
    }
    rows.append(row)
    _write_jsonl(Path(paths.model_calls), rows)
    return row


def list_model_calls(
    *,
    paths: ModelLogPaths,
    tenant_id: str,
    audit_id: Optional[str] = None,
) -> List[Dict[str, object]]:
    rows = _read_jsonl(Path(paths.model_calls))
    scoped = [row for row in rows if str(row["tenant_id"]) == tenant_id]
    if audit_id:
        scoped = [row for row in scoped if str(row["audit_id"]) == audit_id]
    scoped.sort(key=lambda row: (row["created_at"], row["call_id"]))
    return scoped
