# Decision Engine

The deployment decision must be config-driven.

## Inputs
- control_results
- severity of missing controls
- average confidence

## Outputs
- APPROVED
- CONDITIONALLY_APPROVED
- BLOCKED

## Blocking Rule
Block when:
- critical missing controls meet threshold
- high missing controls meet threshold
- average confidence falls below minimum threshold

## Purpose
Prevent placeholder decisions and enforce deterministic review logic.
