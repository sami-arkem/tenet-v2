# Tenet Build Roadmap

## North Star
Tenet should be an end-to-end global compliance intelligence platform, with the model doing deep structured compliance reasoning across all domains and jurisdictions, and Claude turning that into world-class reports.

## Current Phase
Step 0.4 - RAG brain MVP

## Completed
- clean corpus baseline built
- first retrieval corpus prepared
- enterprise output schema defined
- Claude report-layer direction defined
- MVP scope defined
- MVP scope defined

## Now
- MVP scope locked
- output schema locked
- chunk + metadata pipeline built
- retrieval layer built
- reasoning pipeline built
- build evals
- then connect Claude report layer

## Next
- reviewer workflow
- pilot audits
- remediation tracking
- export layer

## Later
- fine-tuning
- broader jurisdictions
- deeper industry coverage
- automation depth

## Next Build Priority

### Deterministic Audit Planning + Control Evaluation Layer

Rationale:
The current system can retrieve and reason, but regulator-ready output quality requires a deterministic audit skeleton between intake and final findings.

Deliverables:
- machine-readable control library
- audit plan generator
- control evaluation engine
- stronger missing_controls and missing_evidence logic
- more defensible confidence assessment

This step is higher priority than UI expansion and should precede major report-layer sophistication work.
