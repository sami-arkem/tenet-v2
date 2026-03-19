from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional


FINALIZE_HARD_BLOCKER_SCHEMA_VERSION = "1.0"


def _stable_json_hash(payload: Dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class FinalizeDecision:
    schema_version: str
    finalize_status: str
    finalize_ready: bool
    release_package_created: bool
    release_package_path: Optional[str]
    blocking_reasons: List[str]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def load_artifact(path: Path) -> Dict[str, object]:
    return _read_json(path)


def build_finalize_decision(
    *,
    finalize_release_artifact: Dict[str, object],
    release_package_path: str,
) -> FinalizeDecision:
    finalize_status = str(finalize_release_artifact.get("finalize_status", "BLOCKED")).upper()
    finalize_ready = bool(finalize_release_artifact.get("finalize_ready", False))

    blocking_reasons = [str(x) for x in finalize_release_artifact.get("blocking_reasons", [])]

    release_package_created = finalize_status == "PASS" and finalize_ready

    payload = {
        "schema_version": FINALIZE_HARD_BLOCKER_SCHEMA_VERSION,
        "finalize_status": "PASS" if release_package_created else "BLOCKED",
        "finalize_ready": release_package_created,
        "release_package_created": release_package_created,
        "release_package_path": release_package_path if release_package_created else None,
        "blocking_reasons": [] if release_package_created else blocking_reasons,
    }

    return FinalizeDecision(
        schema_version=payload["schema_version"],
        finalize_status=payload["finalize_status"],
        finalize_ready=payload["finalize_ready"],
        release_package_created=payload["release_package_created"],
        release_package_path=payload["release_package_path"],
        blocking_reasons=payload["blocking_reasons"],
        payload_hash=_stable_json_hash(payload),
    )


def write_finalize_decision(path: Path, decision: FinalizeDecision) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(decision.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
