from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional


FINAL_RELEASE_SURFACE_SCHEMA_VERSION = "1.1"


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
        if line:
            rows.append(json.loads(line))
    return rows


@dataclass(frozen=True)
class ReleaseSurfaceArtifact:
    schema_version: str
    release_status: str
    release_ready: bool
    final_execution_status: str
    final_execution_ready: bool
    remediation_status: str
    remediation_ready: bool
    report_ready: bool
    export_ready: bool
    total_jobs: int
    total_completed_jobs: int
    total_open_jobs: int
    blocking_reasons: List[str]
    included_artifacts: List[str]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def load_artifact(path: Path) -> Dict[str, object]:
    return _read_json(path)


def load_jobs(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["job_id"]))
    return rows


def build_release_surface(
    *,
    final_execution_discipline: Dict[str, object],
    runner_index: Dict[str, object],
    remediation_gate: Optional[Dict[str, object]] = None,
    report_gate: Optional[Dict[str, object]] = None,
    export_gate: Optional[Dict[str, object]] = None,
) -> ReleaseSurfaceArtifact:
    final_execution_status = str(final_execution_discipline.get("overall_status", "BLOCKED")).upper()
    final_execution_ready = bool(final_execution_discipline.get("discipline_ready", False))

    remediation_status = str(remediation_gate.get("gate_status", "UNKNOWN")).upper() if remediation_gate else "UNKNOWN"
    remediation_ready = bool(remediation_gate.get("remediation_ready", False)) if remediation_gate else False

    total_jobs = int(runner_index.get("total_existing_jobs", 0))
    total_completed_jobs = int(runner_index.get("total_completed_jobs", 0))
    total_open_jobs = int(runner_index.get("total_open_jobs", 0))

    report_ready = bool(report_gate.get("validation_ready", False)) if report_gate else False
    export_ready = bool(export_gate.get("export_ready", False)) if export_gate else False

    blocking_reasons: List[str] = []

    for reason in final_execution_discipline.get("blocking_reasons", []):
        blocking_reasons.append(f"final_execution:{reason}")

    if remediation_gate is not None:
        for reason in remediation_gate.get("blocking_reasons", []):
            blocking_reasons.append(f"remediation:{reason}")

    if total_open_jobs > 0:
        blocking_reasons.append(f"audit_runner:open_jobs:{total_open_jobs}")

    if not report_ready:
        blocking_reasons.append("report_surface:report_not_ready")

    if not export_ready:
        blocking_reasons.append("export_surface:export_not_ready")

    release_ready = (
        final_execution_ready
        and remediation_ready
        and total_open_jobs == 0
        and report_ready
        and export_ready
    )
    release_status = "PASS" if release_ready else "BLOCKED"

    included_artifacts = [
        "final_execution_discipline",
        "audit_runner_index",
    ]
    if remediation_gate is not None:
        included_artifacts.append("remediation_gate")
    if report_gate is not None:
        included_artifacts.append("report_gate")
    if export_gate is not None:
        included_artifacts.append("export_gate")

    payload = {
        "schema_version": FINAL_RELEASE_SURFACE_SCHEMA_VERSION,
        "release_status": release_status,
        "release_ready": release_ready,
        "final_execution_status": final_execution_status,
        "final_execution_ready": final_execution_ready,
        "remediation_status": remediation_status,
        "remediation_ready": remediation_ready,
        "report_ready": report_ready,
        "export_ready": export_ready,
        "total_jobs": total_jobs,
        "total_completed_jobs": total_completed_jobs,
        "total_open_jobs": total_open_jobs,
        "blocking_reasons": blocking_reasons,
        "included_artifacts": included_artifacts,
    }

    return ReleaseSurfaceArtifact(
        schema_version=payload["schema_version"],
        release_status=payload["release_status"],
        release_ready=payload["release_ready"],
        final_execution_status=payload["final_execution_status"],
        final_execution_ready=payload["final_execution_ready"],
        remediation_status=payload["remediation_status"],
        remediation_ready=payload["remediation_ready"],
        report_ready=payload["report_ready"],
        export_ready=payload["export_ready"],
        total_jobs=payload["total_jobs"],
        total_completed_jobs=payload["total_completed_jobs"],
        total_open_jobs=payload["total_open_jobs"],
        blocking_reasons=payload["blocking_reasons"],
        included_artifacts=payload["included_artifacts"],
        payload_hash=_stable_json_hash(payload),
    )


def write_release_surface(path: Path, artifact: ReleaseSurfaceArtifact) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
