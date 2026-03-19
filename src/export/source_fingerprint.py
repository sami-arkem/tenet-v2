from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def capture_source_fingerprints(paths: Dict[str, Path]) -> Dict[str, str]:
    return {name: file_sha256(path) for name, path in paths.items()}


def assert_source_fingerprints_unchanged(paths: Dict[str, Path], expected: Dict[str, str]) -> None:
    current = capture_source_fingerprints(paths)
    changed = [name for name, digest in current.items() if expected.get(name) != digest]
    if changed:
        raise RuntimeError(f"Export blocked: source files changed after validation: {changed}")
