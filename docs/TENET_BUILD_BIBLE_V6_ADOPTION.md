# Tenet Final Build Bible Adoption

This repo now treats `/Users/samisayyed/Downloads/final bible final version.md` as the governing product and architecture specification.

Repo-operational law lives in [AGENTS.md](/Users/samisayyed/tenet-v2/AGENTS.md). Where the final bible is the complete product specification, `AGENTS.md` is the implementation law contributors must follow inside this codebase.

Current deterministic slices already aligned to the v6 operating model:
- evidence intake, planning, readiness, execution, reporting, release, remediation, and review
- lawful real-corpus fetch, promotion, freshness, refresh, and regulatory monitoring
- deterministic notification outbox and signed webhook delivery
- deterministic schedules and Bible-spec schedule policy planning

Adoption rules:
- if a behavior is not in the governing bible or a reconciled repo truth surface, it is not treated as shipped
- new work must update automated tests immediately and preserve deterministic verdict boundaries
- orchestration layers such as corpus refresh, alerts, notifications, webhooks, and schedules must remain downstream of verdict logic
- truth surfaces must stay immutable or ledgered wherever state changes matter

Verification entrypoints:
```bash
python -m pytest tests -q
python -m py_compile core/*.py api/*.py api/routers/*.py
python scripts/bible_alignment_gate.py --strict
PYTHONPATH=. python scripts/proof_density_lane.py --strict
PYTHONPATH=. python scripts/final_execution_discipline.py
python scripts/tenet_program_control.py --strict
```
