from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional


FINAL_EXECUTION_DISCIPLINE_SCHEMA_VERSION = "1.1"


def _stable_json_hash(payload: Dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class FinalExecutionGateStatus:
    gate_name: str
    gate_status: str
    dependency_ready: bool
    blocking_reasons: List[str]
    payload_hash: Optional[str]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FinalExecutionDisciplineArtifact:
    schema_version: str
    overall_status: str
    discipline_ready: bool
    failing_gate_names: List[str]
    blocking_reasons: List[str]
    evaluated_gates: List[FinalExecutionGateStatus]
    total_gates_evaluated: int
    total_blocked_gates: int
    total_passed_gates: int
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "overall_status": self.overall_status,
            "discipline_ready": self.discipline_ready,
            "failing_gate_names": self.failing_gate_names,
            "blocking_reasons": self.blocking_reasons,
            "evaluated_gates": [gate.to_dict() for gate in self.evaluated_gates],
            "total_gates_evaluated": self.total_gates_evaluated,
            "total_blocked_gates": self.total_blocked_gates,
            "total_passed_gates": self.total_passed_gates,
            "payload_hash": self.payload_hash,
        }


def load_gate_artifact(path: Path) -> Dict[str, object]:
    return _read_json(path)


def _normalize_gate(
    *,
    artifact: Dict[str, object],
    fallback_gate_name: str,
    ready_field_candidates: List[str],
) -> FinalExecutionGateStatus:
    gate_name = str(artifact.get("gate_name", fallback_gate_name))
    gate_status = str(artifact.get("gate_status", "UNKNOWN")).upper()

    dependency_ready = False
    for field in ready_field_candidates:
        if field in artifact:
            dependency_ready = bool(artifact[field])
            break

    blocking_reasons = [str(x) for x in artifact.get("blocking_reasons", [])]
    payload_hash = str(artifact["payload_hash"]) if artifact.get("payload_hash") is not None else None

    if gate_status not in {"PASS", "BLOCKED"}:
        gate_status = "BLOCKED"
        if "invalid_gate_status" not in blocking_reasons:
            blocking_reasons.append("invalid_gate_status")

    if gate_status == "PASS" and blocking_reasons:
        gate_status = "BLOCKED"
        dependency_ready = False

    if gate_status == "BLOCKED":
        dependency_ready = False

    return FinalExecutionGateStatus(
        gate_name=gate_name,
        gate_status=gate_status,
        dependency_ready=dependency_ready,
        blocking_reasons=blocking_reasons,
        payload_hash=payload_hash,
    )


def build_final_execution_discipline(
    *,
    schedule_dependency_gate: Dict[str, object],
    remediation_gate: Optional[Dict[str, object]] = None,
    release_gate: Optional[Dict[str, object]] = None,
    export_gate: Optional[Dict[str, object]] = None,
    report_validation_gate: Optional[Dict[str, object]] = None,
    proof_readiness_gate: Optional[Dict[str, object]] = None,
) -> FinalExecutionDisciplineArtifact:
    evaluated_gates: List[FinalExecutionGateStatus] = []

    evaluated_gates.append(
        _normalize_gate(
            artifact=schedule_dependency_gate,
            fallback_gate_name="final_execution_schedule_dependency_gate",
            ready_field_candidates=["dependency_ready", "schedule_runtime_ready"],
        )
    )

    if remediation_gate is not None:
        evaluated_gates.append(
            _normalize_gate(
                artifact=remediation_gate,
                fallback_gate_name="remediation_tracking_gate",
                ready_field_candidates=["remediation_ready", "dependency_ready"],
            )
        )

    if release_gate is not None:
        evaluated_gates.append(
            _normalize_gate(
                artifact=release_gate,
                fallback_gate_name="release_gate",
                ready_field_candidates=["release_ready", "dependency_ready", "schedule_runtime_ready"],
            )
        )

    if export_gate is not None:
        evaluated_gates.append(
            _normalize_gate(
                artifact=export_gate,
                fallback_gate_name="export_gate",
                ready_field_candidates=["export_ready", "dependency_ready", "schedule_runtime_ready"],
            )
        )

    if report_validation_gate is not None:
        evaluated_gates.append(
            _normalize_gate(
                artifact=report_validation_gate,
                fallback_gate_name="report_validation_gate",
                ready_field_candidates=["validation_ready", "dependency_ready", "schedule_runtime_ready"],
            )
        )

    if proof_readiness_gate is not None:
        evaluated_gates.append(
            _normalize_gate(
                artifact=proof_readiness_gate,
                fallback_gate_name="proof_readiness_gate",
                ready_field_candidates=["overall_ready", "dependency_ready", "schedule_runtime_ready"],
            )
        )

    evaluated_gates.sort(key=lambda gate: gate.gate_name)

    failing_gate_names = sorted([gate.gate_name for gate in evaluated_gates if gate.gate_status != "PASS"])
    blocking_reasons: List[str] = []
    for gate in evaluated_gates:
        for reason in gate.blocking_reasons:
            blocking_reasons.append(f"{gate.gate_name}:{reason}")

    overall_status = "PASS" if not failing_gate_names else "BLOCKED"
    discipline_ready = overall_status == "PASS"

    payload = {
        "schema_version": FINAL_EXECUTION_DISCIPLINE_SCHEMA_VERSION,
        "overall_status": overall_status,
        "discipline_ready": discipline_ready,
        "failing_gate_names": failing_gate_names,
        "blocking_reasons": blocking_reasons,
        "evaluated_gates": [gate.to_dict() for gate in evaluated_gates],
        "total_gates_evaluated": len(evaluated_gates),
        "total_blocked_gates": sum(1 for gate in evaluated_gates if gate.gate_status != "PASS"),
        "total_passed_gates": sum(1 for gate in evaluated_gates if gate.gate_status == "PASS"),
    }

    return FinalExecutionDisciplineArtifact(
        schema_version=payload["schema_version"],
        overall_status=payload["overall_status"],
        discipline_ready=payload["discipline_ready"],
        failing_gate_names=payload["failing_gate_names"],
        blocking_reasons=payload["blocking_reasons"],
        evaluated_gates=evaluated_gates,
        total_gates_evaluated=payload["total_gates_evaluated"],
        total_blocked_gates=payload["total_blocked_gates"],
        total_passed_gates=payload["total_passed_gates"],
        payload_hash=_stable_json_hash(payload),
    )


def write_final_execution_discipline(path: Path, artifact: FinalExecutionDisciplineArtifact) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
