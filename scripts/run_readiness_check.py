import json

from src.workflow.readiness import build_readiness_summary

summary = build_readiness_summary()
print(json.dumps(summary, indent=2))
