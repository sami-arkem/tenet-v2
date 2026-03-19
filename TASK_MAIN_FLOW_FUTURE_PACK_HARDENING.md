You are working inside the Tenet repo.

Goal:
Harden the main Tenet flow so future-pack audit types and jurisdictions are treated as first-class deterministic audit inputs across planning, retrieval, reporting, and export.

Requirements:
1. Add tests that run deterministic reason() for:
   - fraud_readiness_review in US
   - transaction_screening_review in EU
   - regulatory_licensing_readiness_review in UAE
   - remediation_tracking_review in CANADA
2. Ensure pack-composed controls, regimes, evidence categories, and query seeds appear in runtime preparation.
3. Ensure reporting/export scripts can run against at least one future-pack case without code changes.
4. Keep model usage at zero for this hardening task.
5. Keep py_compile and pytest green.

Deliver:
- code changes
- tests
- py_compile passing
- pytest passing
