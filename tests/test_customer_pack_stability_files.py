from pathlib import Path

PACKS = [
    "us_aml_enterprise_pack",
    "eu_sanctions_wallet_pack",
    "uae_licensing_vendor_pack",
    "canada_remediation_pack",
]

def test_customer_packs_exist():
    for pack in PACKS:
        pack_dir = Path("data/customer_evidence_packs") / pack
        assert pack_dir.exists()
        assert (pack_dir / "audit_context.json").exists()
