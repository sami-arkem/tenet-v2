# GOLD TESTS

## 1. clean_individual_pass
- task: kyc_screening
- input: Sarah Johnson, individual, GB
- expected_decision: PASS
- expected_risk_band: LOW

## 2. sanctioned_individual_fail
- task: kyc_screening
- input: Viktor Bout, individual, RU
- expected_decision: FAIL
- expected_risk_band: CRITICAL
- must_include: OFAC

## 3. high_risk_company_review
- task: kyb_screening
- input: Crypto Exchange LLC, BVI, cryptocurrency
- expected_risk_band: HIGH or CRITICAL

## 4. eu_ai_act_high_risk
- task: risk_classification
- input: autonomous credit decisioning system, EU
- expected_risk_tier: HIGH_RISK
- must_include: Annex III

## 5. missing_controls_detected
- task: gap_detection
- input: credit scoring system, EU, controls missing
- must_include_missing_controls:
  - human_oversight
  - bias_testing
  - explainability