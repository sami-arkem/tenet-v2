# Tenet

Tenet is a deterministic compliance operating system. The repo’s governing product specification is `/Users/samisayyed/Downloads/final bible final version.md`, operationalized in [AGENTS.md](/Users/samisayyed/tenet-v2/AGENTS.md).

Current implementation focus:
- deterministic audit, report, export, remediation, and review spine
- lawful real-corpus acquisition, freshness, refresh, and regulatory monitoring
- deterministic notification and signed webhook delivery
- deterministic schedule planning and Bible-spec audit schedule policy

Core verification commands:
```bash
python -m pytest tests -q
python -m py_compile core/*.py api/*.py api/routers/*.py
python scripts/bible_alignment_gate.py --strict
PYTHONPATH=. python scripts/proof_density_lane.py --strict
PYTHONPATH=. python scripts/final_execution_discipline.py
python scripts/tenet_program_control.py --strict
```
