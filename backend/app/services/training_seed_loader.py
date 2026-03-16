import json
from pathlib import Path


def load_training_seed():
    path = Path("data/raw/training_seed.jsonl")
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]
