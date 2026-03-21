from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List


FINALIZATION_ORCHESTRATOR_SCHEMA_VERSION = "1.1"


def _stable_json_hash(payload: Dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class FinalizationReceiptFile:
    path: str
    sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FinalizationReceipt:
    schema_version: str
    finalization_status: str
    finalization_ready: bool
    finalize_decision_status: str
    immutable_package_status: str
    included_files: List[FinalizationReceiptFile]
    blocking_reasons: List[str]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "finalization_status": self.finalization_status,
            "finalization_ready": self.finalization_ready,
            "finalize_decision_status": self.finalize_decision_status,
            "immutable_package_status": self.immutable_package_status,
            "included_files": [item.to_dict() for item in self.included_files],
            "blocking_reasons": self.blocking_reasons,
            "payload_hash": self.payload_hash,
        }


def load_artifact(path: Path) -> Dict[str, object]:
    return _read_json(path)


def build_finalization_receipt(
    *,
    finalize_decision: Dict[str, object],
    immutable_release_package: Dict[str, object],
) -> FinalizationReceipt:
    finalize_decision_status = str(finalize_decision.get("finalize_status", "BLOCKED")).upper()
    finalize_ready = bool(finalize_decision.get("finalize_ready", False))
    immutable_package_status = str(immutable_release_package.get("package_status", "BLOCKED")).upper()
    package_ready = bool(immutable_release_package.get("package_ready", False))

    blocking_reasons: List[str] = []
    for reason in finalize_decision.get("blocking_reasons", []):
        blocking_reasons.append(f"finalize_decision:{reason}")
    for reason in immutable_release_package.get("blocking_reasons", []):
        blocking_reasons.append(f"immutable_release_package:{reason}")

    included_files: List[FinalizationReceiptFile] = []
    if finalize_ready and package_ready and finalize_decision_status == "PASS" and immutable_package_status == "PASS":
        for row in immutable_release_package.get("included_files", []):
            included_files.append(
                FinalizationReceiptFile(
                    path=str(row["path"]),
                    sha256=str(row["sha256"]),
                )
            )
        included_files.sort(key=lambda item: item.path)
        finalization_status = "PASS"
        finalization_ready = True
        blocking_reasons = []
    else:
        finalization_status = "BLOCKED"
        finalization_ready = False

    payload = {
        "schema_version": FINALIZATION_ORCHESTRATOR_SCHEMA_VERSION,
        "finalization_status": finalization_status,
        "finalization_ready": finalization_ready,
        "finalize_decision_status": finalize_decision_status,
        "immutable_package_status": immutable_package_status,
        "included_files": [item.to_dict() for item in included_files],
        "blocking_reasons": blocking_reasons,
    }

    return FinalizationReceipt(
        schema_version=payload["schema_version"],
        finalization_status=payload["finalization_status"],
        finalization_ready=payload["finalization_ready"],
        finalize_decision_status=payload["finalize_decision_status"],
        immutable_package_status=payload["immutable_package_status"],
        included_files=included_files,
        blocking_reasons=payload["blocking_reasons"],
        payload_hash=_stable_json_hash(payload),
    )


def write_finalization_receipt(path: Path, receipt: FinalizationReceipt) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
