import json
from pathlib import Path

from src.workflow.workflow_runner import run_customer_evidence_pack

PACKS = [
    "data/customer_evidence_packs/us_aml_enterprise_pack",
    "data/customer_evidence_packs/eu_sanctions_wallet_pack",
    "data/customer_evidence_packs/uae_licensing_vendor_pack",
    "data/customer_evidence_packs/canada_remediation_pack",
]

results = []

for pack_dir in PACKS:
    pack_name = Path(pack_dir).name
    try:
        result = run_customer_evidence_pack(pack_dir)
        row = {
            "pack_name": pack_name,
            "status": "success",
            "result": result,
        }
    except Exception as exc:
        row = {
            "pack_name": pack_name,
            "status": "failed",
            "error": str(exc),
        }
    results.append(row)
    print("=" * 100)
    print(json.dumps(row, indent=2))

Path("logs/customer_pack_stability").mkdir(parents=True, exist_ok=True)
Path("logs/customer_pack_stability/raw_results.json").write_text(
    json.dumps(results, indent=2),
    encoding="utf-8",
)
