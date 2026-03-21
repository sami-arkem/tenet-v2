# Final Execution Discipline

## Goal
Give Tenet one deterministic execution command that proves the platform is operationally healthy.

## Required stages
1. py_compile validation
2. pytest validation
3. readiness check
4. live model eval suite
5. customer-pack stability suite
6. workflow smoke checks
7. historical reporting smoke checks
8. final machine-readable summary

## Rules
- fail loudly on any step failure
- write one final JSON artifact under logs/
- keep execution deterministic
- do not mutate audit truth
