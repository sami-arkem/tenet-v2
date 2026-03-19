# Engine Contracts

## Shared Code Contracts
- src/core/constants.py defines canonical enums
- src/core/contracts.py validates audit context
- src/reasoning/audit_plan.py builds deterministic audit plans
- src/reasoning/control_eval.py evaluates controls
- src/reasoning/decision.py determines deployment decision

## Rule
No reasoning step should invent enum values outside canonical constants.
