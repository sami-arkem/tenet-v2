from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.official_corpus_bootstrap_service import bootstrap_official_corpus, seed_official_sources


def main() -> int:
    parser = argparse.ArgumentParser(description="Tenet real-world official corpus adapter")
    parser.add_argument(
        "--mode",
        choices=["seed", "bootstrap"],
        default="bootstrap",
        help="seed only source manifests, or full bootstrap promote+ingest",
    )
    args = parser.parse_args()

    if args.mode == "seed":
        payload = seed_official_sources()
    else:
        payload = bootstrap_official_corpus()

    print(json.dumps(payload, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
