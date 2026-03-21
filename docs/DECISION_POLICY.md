# Decision Policy

## Allowed Output Status

- APPROVED
- CONDITIONALLY_APPROVED
- BLOCKED

## BLOCKED

Use when:
- a critical required control is missing
- sanctions or AML core controls are materially absent
- evidence indicates major control failure
- confidence is too low for safe positive conclusion

## CONDITIONALLY_APPROVED

Use when:
- no critical blocker exists
- some controls are partial
- evidence gaps remain
- remediation is clear and bounded

## APPROVED

Use when:
- no critical or major high-severity control is missing
- evidence is materially sufficient
- confidence is high enough for enterprise review

## Rule

Decision must be driven by:
- control status
- evidence sufficiency
- severity of gaps
- confidence level

Decision must not be set from retrieval presence alone.
