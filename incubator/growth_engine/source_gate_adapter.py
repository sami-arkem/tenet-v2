from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=False) + "\n")


@dataclass(frozen=True)
class GrowthSourceCandidate:
    source_id: str
    title: str
    domain: str
    jurisdictions: list[str]
    countries: list[str]
    source_class: str
    acquisition_method: str
    license_status: str
    owner: str
    source_url: str | None
    approved: bool
    retrieval_allowed: bool
    metadata: dict[str, Any]

    def to_source_manifest(self) -> dict[str, Any]:
        return {
            "source_id": _require_non_empty_str(self.source_id, "source_id"),
            "title": _require_non_empty_str(self.title, "title"),
            "domain": _require_non_empty_str(self.domain, "domain"),
            "jurisdictions": [value for value in self.jurisdictions if isinstance(value, str) and value.strip()],
            "countries": [value for value in self.countries if isinstance(value, str) and value.strip()],
            "source_class": _require_non_empty_str(self.source_class, "source_class"),
            "acquisition_method": _require_non_empty_str(self.acquisition_method, "acquisition_method"),
            "license_status": _require_non_empty_str(self.license_status, "license_status"),
            "owner": _require_non_empty_str(self.owner, "owner"),
            "source_url": self.source_url.strip() if isinstance(self.source_url, str) and self.source_url.strip() else None,
            "approved": bool(self.approved),
            "retrieval_allowed": bool(self.retrieval_allowed),
            "metadata": dict(self.metadata or {}),
        }


def write_candidate_manifest(candidate: GrowthSourceCandidate, output_path: Path) -> dict[str, Any]:
    manifest = candidate.to_source_manifest()
    _atomic_write_json(output_path, manifest)
    return manifest
