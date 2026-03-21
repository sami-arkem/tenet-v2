import json
import sys

from src.workflow.workflow_runner import run_customer_evidence_pack

if len(sys.argv) != 2:
    raise SystemExit("Usage: PYTHONPATH=. python scripts/run_customer_evidence_pack.py <pack_dir>")

result = run_customer_evidence_pack(sys.argv[1])
print(json.dumps(result, indent=2))
