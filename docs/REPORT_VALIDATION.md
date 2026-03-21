# Report Validation

## Goal
Ensure report outputs remain faithful to locked audit JSON.

## Rules
- report must not change deployment decision
- report must not invent findings
- report must not invent missing controls
- report must contain required sections
- report tone may improve, but facts may not drift

## Validation checks
- required headings exist
- deployment decision matches audit JSON
- key finding titles are reflected
- missing control IDs referenced in regulator/client outputs when relevant
