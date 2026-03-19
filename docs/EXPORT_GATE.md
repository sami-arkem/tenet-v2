# Export Gate

## Goal
Allow DOCX/PDF export only when report outputs have already passed deterministic validation.

## Rules
- export must fail if report validation fails
- export must never modify audit truth
- export must use locked markdown inputs only
- export layer is formatting only, never reasoning

## Inputs
- logs/report_audit_output.json
- logs/board_memo.md
- logs/regulator_memo.md
- logs/client_report.md

## Outputs
- logs/exports/board_memo.docx
- logs/exports/regulator_memo.docx
- logs/exports/client_report.docx
- logs/exports/board_memo.pdf
- logs/exports/regulator_memo.pdf
- logs/exports/client_report.pdf
