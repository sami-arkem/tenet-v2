# MODEL CONTRACT

## 1. kyc_screening
### input
- full_name
- date_of_birth_optional
- nationality_optional
- country_optional
- entity_type

### output
- task
- entity_name
- risk_score
- risk_band
- decision
- match_status
- findings
- matched_sources
- recommended_actions
- confidence

### required_fields
- task
- entity_name
- risk_score
- risk_band
- decision
- findings
- confidence

### pass_fail_rule
- PASS = no sanctions match and low risk
- REVIEW = possible match or missing critical data
- FAIL = confirmed sanctions or prohibited onboarding

## 2. kyb_screening
### input
- company_name
- jurisdiction
- industry
- incorporation_country_optional
- ownership_info_optional

### output
- task
- company_name
- risk_score
- risk_band
- decision
- risk_factors
- findings
- recommended_actions
- confidence

### required_fields
- task
- company_name
- risk_score
- risk_band
- decision
- risk_factors
- findings
- confidence

### pass_fail_rule
- PASS = normal business and low risk jurisdiction
- REVIEW = elevated risk factors
- FAIL = prohibited or extreme risk profile

## 3. risk_classification
### input
- system_name
- system_description
- jurisdiction
- use_case
- sector

### output
- task
- system_name
- overall_risk_score
- risk_tier
- triggered_categories
- applicable_regulations
- required_controls
- findings
- recommended_actions
- confidence

### required_fields
- task
- system_name
- overall_risk_score
- risk_tier
- triggered_categories
- required_controls
- findings
- confidence

### pass_fail_rule
- PASS = correct tier and correct triggered categories
- FAIL = wrong tier or missing major regulatory trigger

## 4. gap_detection
### input
- system_name
- jurisdiction
- system_type
- controls_present

### output
- task
- system_name
- overall_gap_score
- missing_controls
- control_gaps
- findings
- recommended_actions
- confidence

### required_fields
- task
- system_name
- overall_gap_score
- missing_controls
- control_gaps
- findings
- confidence

### pass_fail_rule
- PASS = all major missing controls correctly identified
- FAIL = misses critical control gaps

## 5. document_compliance_analysis
### input
- document_name
- document_type
- document_text
- jurisdiction

### output
- task
- document_name
- risk_score
- triggered_obligations
- identified_gaps
- findings
- recommended_actions
- confidence

### required_fields
- task
- document_name
- risk_score
- triggered_obligations
- identified_gaps
- findings
- confidence

### pass_fail_rule
- PASS = obligations and gaps correctly extracted
- FAIL = misses major obligations or invents unsupported ones
