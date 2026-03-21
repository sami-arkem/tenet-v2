# Tenet Growth Engine Incubator

This folder is intentionally outside the canonical Tenet runtime.

Purpose:
- preserve high-upside growth and acquisition ideas without polluting the deterministic compliance spine
- force any future growth automation to enter through Tenet's lawful source-acquisition gate
- keep compliance product truth separate from revenue-side experimentation

Non-negotiable rules:
- nothing in this folder is part of audit verdicting, release gating, or deterministic audit truth
- nothing here auto-runs in production
- any future crawler, monitor, or enrichment bot must emit source manifests compatible with `core/source_acquisition_service.py`
- unauthorized scraping, prohibited licensing, or robots-blocked sources remain blocked by the canonical source gate

Current contents:
- `source_gate_adapter.py`
  Real adapter for converting future growth-side candidates into canonical source manifests.
- `bot_catalog.md`
  Curated catalog of possible growth modules extracted from the broader idea set, grouped into safe future work areas.

This keeps the opportunity alive while respecting the build bible and `AGENTS.md`.
