from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional


FINALIZE_RELEASE_BRIDGE_SCHEMA_VERSION = "1.0"


def _stable_json_hash(payload: Dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        return []
    rows: List[Dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


@dataclass(frozen=True)
class FinalizeReleaseArtifact:
    schema_version: str
    finalize_status: str
    finalize_ready: bool
    release_surface_status: str
    release_surface_ready: bool
    execution_complete: bool
    report_ready: bool
    export_ready: bool
    total_execution_records: int
    total_completed_executions: int
    total_open_executions: int
    total_blocked_executions: int
    blocking_reasons: List[str]
    included_artifacts: List[str]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def load_artifact(path: Path) -> Dict[str, object]:
    return _read_json(path)


def load_execution_records(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(
        key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["execution_id"])
    )
    return rows


def build_finalize_release_artifact(
    *,
    release_surface: Dict[str, object],
    execution_index: Dict[str, object],
    execution_records: List[Dict[str, object]],
) -> FinalizeReleaseArtifact:
    release_surface_status = str(release_surface.get("release_status", "BLOCKED")).upper()
    release_surface_ready = bool(release_surface.get("release_ready", False))

    total_execution_records = len(execution_records)
    total_completed_executions = int(execution_index.get("total_completed_executions", 0))
    total_open_executions = int(execution_index.get("total_open_executions", 0))
    total_blocked_executions = int(execution_index.get("total_blocked_executions", 0))

    report_ready = all(bool(row.get("report_ready", False)) for row in execution_records) if execution_records else False
    export_ready = all(bool(row.get("export_ready", False)) for row in execution_records) if execution_records else False
    execution_complete = total_execution_records > 0 and total_open_executions == 0 and total_blocked_executions == 0

    blocking_reasons: List[str] = []

    for reason in release_surface.get("blocking_reasons", []):
        blocking_reasons.append(f"release_surface:{reason}")

    if not execution_complete:
        blocking_reasons.append(f"audit_execution:execution_not_complete:{total_open_executions}")

    if not report_ready:
        blocking_reasons.append("audit_execution:report_not_ready_for_all_records")

    if not export_ready:
        blocking_reasons.append("audit_execution:export_not_ready_for_all_records")

    finalize_ready = release_surface_ready and execution_complete and report_ready and export_ready
    finalize_status = "PASS" if finalize_ready else "BLOCKED"

    included_artifacts = [
        "release_surface",
        "audit_execution_index",
        "audit_execution_records",
    ]

    payload = {
        "schema_version": FINALIZE_RELEASE_BRIDGE_SCHEMA_VERSION,
        "finalize_status": finalize_status,
        "finalize_ready": finalize_ready,
        "release_surface_status": release_surface_status,
        "release_surface_ready": release_surface_ready,
        "execution_complete": execution_complete,
        "report_ready": report_ready,
        "export_ready": export_ready,
        "total_execution_records": total_execution_records,
        "total_completed_executions": total_completed_executions,
        "total_open_executions": total_open_executions,
        "total_blocked_executions": total_blocked_executions,
        "blocking_reasons": blocking_reasons,
        "included_artifacts": included_artifacts,
    }

    return FinalizeReleaseArtifact(
        schema_version=payload["schema_version"],
        finalize_status=payload["finalize_status"],
        finalize_ready=payload["finalize_ready"],
        release_surface_status=payload["release_surface_status"],
        release_surface_ready=payload["release_surface_ready"],
        execution_complete=payload["execution_complete"],
        report_ready=payload["report_ready"],
        export_ready=payload["export_ready"],
        total_execution_records=payload["total_execution_records"],
        total_completed_executions=payload["total_completed_executions"],
        total_open_executions=payload["total_open_executions"],
        total_blocked_executions=payload["total_blocked_executions"],
        blocking_reasons=payload["blocking_reasons"],
        included_artifacts=payload["included_artifacts"],
        payload_hash=_stable_json_hash(payload),
    )


def write_finalize_release_artifact(path: Path, artifact: FinalizeReleaseArtifact) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
