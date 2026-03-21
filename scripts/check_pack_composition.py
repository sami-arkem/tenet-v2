from src.core.pack_composer import compose_pack_view

cases = [
    {
        "audit_type": "aml_readiness_review",
        "jurisdictions": ["US"],
    },
    {
        "audit_type": "sanctions_readiness_review",
        "jurisdictions": ["US", "EU"],
    },
    {
        "audit_type": "vendor_internal_compliance_readiness_review",
        "jurisdictions": ["US", "UK", "EU"],
    },
    {
        "audit_type": "policy_governance_gap_analysis",
        "jurisdictions": ["EU"],
    },
]

for ctx in cases:
    view = compose_pack_view(ctx)
    print("=" * 80)
    print("audit_type:", ctx["audit_type"])
    print("jurisdictions:", view["jurisdictions"])
    print("domains:", view["domains"])
    print("regimes:", view["regimes"])
    print("controls:", view["controls"])
    print("evidence_categories:", view["evidence_categories"])
    print("query_seeds:", view["query_seeds"])
