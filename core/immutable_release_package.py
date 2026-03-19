from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional


IMMUTABLE_RELEASE_PACKAGE_SCHEMA_VERSION = "1.0"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_json_hash(payload: Dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class ReleasePackageFile:
    path: str
    sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ImmutableReleasePackage:
    schema_version: str
    package_status: str
    package_ready: bool
    finalize_status: str
    included_files: List[ReleasePackageFile]
    manifest_path: str
    blocking_reasons: List[str]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "package_status": self.package_status,
            "package_ready": self.package_ready,
            "finalize_status": self.finalize_status,
            "included_files": [item.to_dict() for item in self.included_files],
            "manifest_path": self.manifest_path,
            "blocking_reasons": self.blocking_reasons,
            "payload_hash": self.payload_hash,
        }


def load_artifact(path: Path) -> Dict[str, object]:
    return _read_json(path)


def build_immutable_release_package(
    *,
    finalize_decision: Dict[str, object],
    files_to_include: List[Path],
    manifest_path: Path,
) -> ImmutableReleasePackage:
    finalize_status = str(finalize_decision.get("finalize_status", "BLOCKED")).upper()
    finalize_ready = bool(finalize_decision.get("finalize_ready", False))

    blocking_reasons = [str(x) for x in finalize_decision.get("blocking_reasons", [])]
    included_files: List[ReleasePackageFile] = []

    if finalize_status == "PASS" and finalize_ready:
        for path in files_to_include:
            if not path.exists():
                raise FileNotFoundError(f"release package input missing: {path}")
            included_files.append(
                ReleasePackageFile(
                    path=str(path),
                    sha256=_sha256_file(path),
                )
            )
        included_files.sort(key=lambda item: item.path)
        package_status = "PASS"
        package_ready = True
    else:
        package_status = "BLOCKED"
        package_ready = False
        included_files = []

    payload = {
        "schema_version": IMMUTABLE_RELEASE_PACKAGE_SCHEMA_VERSION,
        "package_status": package_status,
        "package_ready": package_ready,
        "finalize_status": finalize_status,
        "included_files": [item.to_dict() for item in included_files],
        "manifest_path": str(manifest_path),
        "blocking_reasons": [] if package_ready else blocking_reasons,
    }

    return ImmutableReleasePackage(
        schema_version=payload["schema_version"],
        package_status=payload["package_status"],
        package_ready=payload["package_ready"],
        finalize_status=payload["finalize_status"],
        included_files=included_files,
        manifest_path=payload["manifest_path"],
        blocking_reasons=payload["blocking_reasons"],
        payload_hash=_stable_json_hash(payload),
    )


def write_immutable_release_package(path: Path, artifact: ImmutableReleasePackage) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
