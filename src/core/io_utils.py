from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_text(path: str | Path, content: str, encoding: str = "utf-8") -> Path:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(prefix=f".{out_path.name}.", dir=str(out_path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(content)
        tmp_path.replace(out_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return out_path


def atomic_write_json(path: str | Path, obj: Any, *, indent: int = 2, encoding: str = "utf-8") -> Path:
    return atomic_write_text(path, json.dumps(obj, indent=indent), encoding=encoding)
