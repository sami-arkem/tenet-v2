from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def build_export_manifest(audit_id: str, files: Dict[str, Path]) -> Dict[str, object]:
    return {
        "audit_id": audit_id,
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifacts": {
            name: {
                "path": str(path),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for name, path in sorted(files.items())
        },
    }


def write_export_manifest(audit_id: str, files: Dict[str, Path], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_export_manifest(audit_id, files)
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out_path
