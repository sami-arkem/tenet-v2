import json
from pathlib import Path


def load_jsonl(path: str):
    file_path = Path(path)
    with file_path.open() as f:
        return [json.loads(line) for line in f if line.strip()]
