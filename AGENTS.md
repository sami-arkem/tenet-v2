# Repository Guidelines

This file is the executable contributor law for Tenet, derived from `/Users/samisayyed/Downloads/final bible final version.md`. Treat that final bible as the current product, architecture, test, queue, corpus, notification, webhook, and release ground truth. Treat this file as the repo-operational version of that law. If code, UI, workflow, corpus, queue behavior, or release behavior conflicts with this file, the contribution is wrong until reconciled.

## 1. Supreme Mission
Tenet is the operating system for compliance. Build for two users at once:
- the solo compliance officer who needs one obvious path to a defensible audit
- the senior CCO who expects Big 4-grade rigor, auditability, and control

Tenet must feel powerful, invisible, and inevitable. Complexity belongs in the system, never in the operator experience.

If a capability is not specified in the governing bible or a reconciled repo truth surface, it does not exist yet.

## 2. Product Shape
Tenet is not a point tool. It is one compliance spine:
1. evidence intake
2. deterministic planning
3. readiness
4. audit execution
5. report generation
6. immutable export
7. remediation tracking
8. review decision
9. workflow orchestration

Every new feature must strengthen this spine, not create a side system.

Operational systems that now sit on this spine and must stay deterministic:
- lawful real-corpus acquisition, promotion, freshness, refresh, and regulatory monitoring
- notifications, webhooks, and delivery ledgers
- recurring schedules, policy schedules, reminder planning, and due execution planning

## 3. Non-Negotiable Build Law
- No invented evidence, findings, expected outcomes, taxonomy, controls, or sign-off.
- No placeholder text, TODOs, lorem ipsum, `console.log`, `debugger`, or "AI-powered" fluff in production surfaces.
- No slop AI placeholder code, fake model scaffolding, decorative AI abstractions, unwired model pathways, or dummy fallbacks presented as production capability.
- No model-first or UI-first drift. Deterministic runtime, evidence grounding, and reviewability come first.
- No hidden state forks. One canonical object per audit run, one canonical workflow state, one canonical review state.
- No silent mutation of proof artifacts, manifests, ledgers, or gates.
- No decorative enterprise cosplay. Authority must come from clarity, not gimmicks.
- No API endpoint should perform business logic before auth and tenant scope are established where those concepts exist.
- No database or retrieval query should bypass tenant isolation where tenant scope exists.
- No model call should be added without the corresponding logging truth surface.

Testing law:
- Every component must pass both an automated test and a manual test before the next component is treated as complete.
- For core deterministic logic, favor exhaustive branch coverage over broad but shallow happy-path tests.
- Any change that touches the audit engine, truth surfaces, release gates, or gold cases must preserve zero-regression behavior.

## 4. Architecture Law
Canonical backend flow:
`evidence pack -> plan -> readiness -> execution -> report pack -> markdown -> export package -> remediation -> review`

Canonical state surfaces:
- `artifacts/audit_runs/<run_id>/`
- `artifacts/evidence_packs/<pack_id>/`
- `artifacts/workflow_runs/<workflow_id>/`

Core deterministic logic belongs under `core/`.
API surfaces belong under `api/routers/`.
Truth surfaces, ledgers, and proof artifacts belong under `logs/` and `config/`.

Queue-safe automation surfaces belong under deterministic service layers and immutable fixtures/log roots, not hidden in ad hoc helpers. Background work must materialize durable plans, run ledgers, and replayable payloads.

## 5. UI and Design Law
Tenet should feel like Linear, Stripe, Notion, Vercel, or a well-formatted legal document: precise, calm, dense, and obvious.

UI rules:
- no emoji in product UI
- no purple-gradient slop
- no arbitrary hardcoded colors; use tokens
- no badge spam, novelty motion, or modal stacks
- no hidden labels, vague errors, or ambiguous primary actions

Design tone: precision, authority, calm.

## 6. Proof and Corpus Law
Historical context may inform but never override current audit truth.

Gold cases require:
- `audit_context.json`
- `expected_assertions.json`
- `case_notes.md`

Required truth flags:
- `historical_context_is_non_authoritative: true`
- `deterministic_current_audit_truth_only: true`
- `authoritative_current_audit_truth: true` where applicable

Safe autofix may normalize schema and trivial structure. It must never invent semantics.

Real-corpus law:
- Only approved official, licensed, or customer-authorized sources may enter the corpus path.
- Every fetch, normalization, promotion, refresh, and monitor run must leave a provenance trail and immutable ledger.
- Corpus freshness, refresh, alerts, notifications, webhooks, and schedules remain downstream of verdict logic. They may inform operators and orchestration, never mutate deterministic audit truth.

## 7. Coding Standards
- Python-first, typed, deterministic, explicit
- 4-space indentation
- small helpers over large opaque functions
- sparse factual comments only where needed
- preserve machine-readable JSON contracts
- use transactional writes, backups, and ledgers for stateful flows

Prefer repo-wide clarity over cleverness.

## 8. Release and Readiness Law
Tenet is not ready because a page renders or an endpoint returns 200. It is ready only when the governing truth surfaces and tests are green.

Minimum bar:
- focused tests passing
- owning gate green
- no new program-control blocker
- no placeholder artifacts
- updated logs/manifests where required

Authoritative commands:
```bash
python -m pytest tests -q
python -m py_compile core/*.py api/*.py api/routers/*.py
PYTHONPATH=. python scripts/proof_density_lane.py --strict
PYTHONPATH=. python scripts/final_execution_discipline.py
python scripts/bible_alignment_gate.py --strict
python scripts/tenet_program_control.py --strict
```

## 9. Agent Instructions
Do not improvise around the bible. Build the specified system. Prefer strengthening the canonical compliance spine over adding adjacent features. When asked for readiness, check the live truth surface first and act against the highest real blocker. Truth beats optimism.
Treat this file and the final build bible as persistent governing law for every change, even when conversational context is compressed. Check meaningful code, workflow, retrieval, corpus, queue, model, and release changes against both before considering the work complete.

---

## 10. Execution Mode — Code Task Response Format

When helping with code tasks, respond with exactly this structure:

### 1. WHERE WE ARE
One short paragraph. Verified facts only. No inflated claims.

### 2. NEXT BEST MOVE
One concise paragraph. Exactly one move. No branching roadmap. No optional strategy tree.

### 3. EXECUTABLE BLOCK
One large executable code block only. Real code or shell commands. No pseudo-code. No scattered fragments.

### 4. VERIFY
One short paragraph. State what is verified. State what is not verified. State which tests were run.

---

## 11. Model Usage Policy

Models are allowed only for:
- classification
- key-fact extraction
- gap narration
- report narrative

Models are NOT allowed for:
- verdicts
- pass/fail control decisions
- deterministic audit decision logic
- evidence sufficiency verdicts
- release decisioning

Authority order:
1. deterministic verdict core
2. retrieval / evidence ingestion / constrained extraction
3. model augmentation only on approved surfaces
4. broader model usage later, never for verdicts

Never move verdict logic into models.

---

## 12. Deterministic System Rules

- deterministic audit core
- strict evidence grounding
- human-reviewable output
- reusable control/regime library
- production-grade only
- no fake placeholders
- no invented strong-pass outcomes
- no sloppy code
- no "AI vibes" architecture
- no weakening validation gates
- no weakening export gates
- no breaking evals silently
- historical context must never override current audit truth
- current audit truth is always authoritative
- no pretending code exists if not verified
- no claiming something is complete unless verified in repo/tests
