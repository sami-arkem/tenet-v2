from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.remediation_operator_service import (
    RemediationOperatorPaths,
    bootstrap_from_generated_remediation,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap operator-driven remediation workspace from generated remediation items.")
    parser.add_argument("--generated-items", default="state/remediation/remediation_items.jsonl")
    parser.add_argument("--items", default="state/remediation/remediation_items_operator.jsonl")
    parser.add_argument("--timeline", default="state/remediation/remediation_timeline.jsonl")
    parser.add_argument("--index", default="state/remediation/remediation_lifecycle_index.json")
    parser.add_argument("--gate", default="state/remediation/remediation_gate.json")
    parser.add_argument("--evidence-metadata", default="state/remediation/remediation_evidence_metadata.jsonl")
    parser.add_argument("--notification-outbox", default="state/remediation/remediation_notification_outbox.jsonl")
    parser.add_argument("--operator-audit-log", default="state/remediation/remediation_operator_audit_log.jsonl")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = RemediationOperatorPaths(
        items=args.items,
        timeline=args.timeline,
        lifecycle_index=args.index,
        gate=args.gate,
        evidence_metadata=args.evidence_metadata,
        notification_outbox=args.notification_outbox,
        operator_audit_log=args.operator_audit_log,
    )
    result = bootstrap_from_generated_remediation(
        generated_items_path=Path(args.generated_items),
        operator_paths=paths,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
