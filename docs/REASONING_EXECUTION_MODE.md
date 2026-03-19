# Reasoning Execution Mode

## Principle

Tenet uses deterministic reasoning as the safety spine.

Model reasoning is layered on top as a controlled upgrade, not as an uncontrolled replacement.

## Execution order

1. validate audit context
2. build audit plan
3. retrieve evidence
4. run deterministic control evaluation
5. build deterministic baseline output
6. optionally run model_reasoner
7. overlay only approved narrative sections
8. return final schema-safe output

## Why

This preserves:
- structural reliability
- evidence-aware decision logic
- stable fallback behavior
- safer production execution

## Model overlay policy

The model may improve:
- executive_summary
- findings
- key_risks
- remediation_roadmap
- reporting_outputs

The deterministic layer remains authoritative for:
- audit_scope
- regulatory_applicability
- deployment_decision
- financial_exposure
- control_assessment
- confidence_assessment
- evidence_appendix
- missing_controls
- missing_evidence
