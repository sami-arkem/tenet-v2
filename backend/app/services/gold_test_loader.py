import json
from pathlib import Path


def load_gold_tests():
    path = Path("data/gold/gold_tests.jsonl")
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]
