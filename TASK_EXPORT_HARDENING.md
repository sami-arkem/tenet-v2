You are working inside the Tenet repo.

Goal:
Harden the export layer so Tenet produces enterprise-safe DOCX and PDF artifacts only from validated markdown.

Requirements:
1. Add deterministic export manifest generation:
   - report file paths
   - sha256 checksums
   - export timestamp
   - source audit_id
2. Add tests for manifest correctness.
3. Add deterministic filenames including audit_id and report type.
4. Add a failure if any markdown source changes after validation but before export.
5. Keep exporter formatting-only; never change audit truth.
6. Keep cost at zero for export path.

Deliver:
- code changes
- tests
- py_compile passing
- pytest passing
