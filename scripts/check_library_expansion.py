from src.core.library_loader import (
    control_ids_for_audit_type,
    regime_ids_for_audit_type_and_jurisdictions,
)

audit_types = [
    "aml_readiness_review",
    "kyc_kyb_policy_and_control_review",
    "sanctions_readiness_review",
    "policy_governance_gap_analysis",
    "vendor_internal_compliance_readiness_review",
]

for audit_type in audit_types:
    controls = control_ids_for_audit_type(audit_type)
    regimes = regime_ids_for_audit_type_and_jurisdictions(audit_type, ["US", "UK", "EU"])
    print("=" * 80)
    print("audit_type:", audit_type)
    print("controls:", controls)
    print("regimes:", regimes)
