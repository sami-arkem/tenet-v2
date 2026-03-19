# Tenet Execution Skill

This skill encodes the Tenet deterministic compliance platform execution patterns for AI assistants.

## Purpose

Enable AI assistants to execute code tasks within the Tenet repository while preserving:
- Deterministic audit core authority
- Evidence grounding
- Production-grade rigor
- Bible-aligned architecture

## When to Use

Invoke this skill when:
- Implementing features in the Tenet compliance platform
- Modifying core deterministic logic
- Adding tests for audit/review/export workflows
- Working with schedule policies, reminders, or due execution
- Handling evidence packs, corpus ingestion, or freshness tracking

## Execution Pattern

### 1. Verify Repo Truth First
- Read existing files before modifying
- Check test patterns in `tests/`
- Confirm module locations in `core/`
- Never assume—always inspect

### 2. Follow Architecture Law
- Core logic → `core/`
- API surfaces → `api/routers/`
- State surfaces → `artifacts/`, `logs/`, `config/`
- Tests → `tests/`

### 3. Preserve Deterministic Rules
- No model-based verdicts
- No fake evidence or outcomes
- No weakening validation/export/release gates
- Historical context never overrides current audit truth

### 4. Response Format
For code tasks, respond with exactly:

```
### 1. WHERE WE ARE
[Verified facts only, one paragraph]

### 2. NEXT BEST MOVE
[One concise move, no branching roadmap]

### 3. EXECUTABLE BLOCK
[One large code block with real code/commands]

### 4. VERIFY
[What's verified, what's not, test results]
```

### 5. Testing Requirements
- Write tests alongside code
- Run tests before claiming completion
- Report actual test results honestly
- Never claim "green" without running

## Model Usage Boundaries

**Allowed:**
- Classification
- Key-fact extraction
- Gap narration
- Report narrative

**Not Allowed:**
- Verdict logic
- Pass/fail decisions
- Evidence sufficiency
- Release decisioning

## Key Modules

### Audit Schedule Policy
- `core/audit_schedule_policy.py` — Canonical policy engine
- `core/audit_schedule_runtime.py` — Runtime orchestrator
- Frequencies: MANUAL, MONTHLY, QUARTERLY, BIANNUAL, ANNUAL, CUSTOM
- Stale evidence threshold: 60 days
- Reminder window: 7 days before due date

### Schedule Services
- `core/schedule_policy_service.py` — File-based policy persistence
- `core/schedule_service.py` — Schedule CRUD and execution

### Evidence & Corpus
- `core/evidence_ingestion_service.py`
- `core/evidence_pack_service.py`
- `core/official_corpus_bootstrap_service.py`
- `core/dataset_freshness_service.py`

### Reporting & Export
- `core/report_composer.py`
- `core/export_package.py`
- `core/release_gate_service.py`

## Verification Commands

```bash
# Run specific tests
python -m pytest tests/test_audit_schedule_policy.py tests/test_audit_schedule_runtime.py -v

# Run all tests
python -m pytest tests -q

# Compile check
python -m py_compile core/*.py

# Bible alignment gate
python scripts/bible_alignment_gate.py --strict
```

## Anti-Patterns to Avoid

- "We should rebuild this entire subsystem"
- "I assume module X already does Y"
- "Done" without test evidence
- "Green" without running tests
- "Bible complete" without verification
- Giant speculative redesigns
- Broad abstractions without need
- TODO-driven skeletons presented as complete

## Success Criteria

Code is ready when:
- Focused tests pass
- No regressions in related tests
- Deterministic gates preserved
- No placeholder artifacts
- Logs/manifests updated where required
