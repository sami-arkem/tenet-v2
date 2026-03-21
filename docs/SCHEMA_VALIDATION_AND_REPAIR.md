# Schema Validation And Repair

## Goal

Keep Tenet outputs structurally reliable even when the model is imperfect.

## Validation policy

- allow only keys that exist in the output schema template
- fill missing keys from the template
- recursively repair nested objects
- coerce obvious primitive mismatches conservatively
- preserve list structure only when list values are valid for the expected field shape

## Repair philosophy

Repair structure, not substance.

This means:
- add missing sections
- trim unsupported keys
- normalize obvious type mismatches
- do not invent evidence, findings, or controls

## Hard rule

If output still cannot be repaired into schema shape, fail loudly.
