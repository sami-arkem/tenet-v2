from src.core.pack_loader import load_jurisdiction_packs, load_domain_packs
from src.core.pack_composer import compose_pack_view

print("FUTURE JURISDICTIONS")
for key in ["UAE", "SINGAPORE", "HONG_KONG", "CANADA", "AUSTRALIA"]:
    pack = load_jurisdiction_packs()[key]
    print(key, pack["regimes"], pack["supported_domains"])

print("\nFUTURE DOMAINS")
for key in ["fraud", "transaction_screening", "regulatory_licensing", "remediation_tracking"]:
    pack = load_domain_packs()[key]
    print(key, pack["control_ids"], pack["query_seeds"])

print("\nCOMPOSITION CHECKS")
cases = [
    {
        "audit_type": "sanctions_readiness_review",
        "jurisdictions": ["UAE"],
        "domains": ["sanctions", "transaction_screening", "governance"],
    },
    {
        "audit_type": "vendor_internal_compliance_readiness_review",
        "jurisdictions": ["CANADA"],
        "domains": ["vendor_risk", "regulatory_licensing", "governance"],
    },
    {
        "audit_type": "policy_governance_gap_analysis",
        "jurisdictions": ["AUSTRALIA"],
        "domains": ["governance", "remediation_tracking"],
    },
]

for ctx in cases:
    view = compose_pack_view(ctx)
    print("=" * 80)
    print("audit_type:", ctx["audit_type"])
    print("jurisdictions:", view["jurisdictions"])
    print("domains:", view["domains"])
    print("controls:", view["controls"])
    print("regimes:", view["regimes"])
    print("query_seeds:", view["query_seeds"])
