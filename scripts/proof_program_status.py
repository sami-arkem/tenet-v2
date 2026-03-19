from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.proof_program import load_registry


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proof_program_status",
        description="Deterministic proof program registry and readiness gate for Tenet.",
    )
    parser.add_argument(
        "--state-path",
        default="state/proof_program/manifest.json",
        help="Path to the proof program manifest.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    targets = subparsers.add_parser("set-targets", help="Set gold case and customer pack targets.")
    targets.add_argument("--gold-target", type=int, required=True)
    targets.add_argument("--customer-pack-target", type=int, required=True)

    add_gold = subparsers.add_parser("add-gold", help="Add or update a gold case.")
    add_gold.add_argument("--case-id", required=True)
    add_gold.add_argument("--title", required=True)
    add_gold.add_argument("--domain", required=True)
    add_gold.add_argument("--jurisdiction", required=True)
    add_gold.add_argument("--framework", required=True)
    add_gold.add_argument("--control-id", required=True)
    add_gold.add_argument("--status", required=True, choices=["PASS", "FAIL", "BLOCKED"])
    add_gold.add_argument("--notes")

    add_pack = subparsers.add_parser("add-pack", help="Add or update a customer evidence pack.")
    add_pack.add_argument("--pack-id", required=True)
    add_pack.add_argument("--customer-name", required=True)
    add_pack.add_argument("--domain", required=True)
    add_pack.add_argument("--jurisdiction", required=True)
    add_pack.add_argument("--framework", required=True)
    add_pack.add_argument("--status", required=True, choices=["ACTIVE", "STABLE", "FAILED", "BLOCKED"])
    add_pack.add_argument("--notes")

    discipline = subparsers.add_parser("set-discipline", help="Record final execution discipline status.")
    discipline.add_argument("--suite-green", action="store_true")
    discipline.add_argument("--suite-red", action="store_true")
    discipline.add_argument("--ref")
    discipline.add_argument(
        "--failing-gate",
        action="append",
        default=[],
        help="Repeatable failing gate name when suite is red.",
    )

    summary = subparsers.add_parser("summary", help="Print deterministic readiness summary.")
    summary.add_argument("--write", action="store_true", help="Write readiness JSON and Markdown artifacts.")
    summary.add_argument("--strict", action="store_true", help="Exit non-zero unless readiness is fully green.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    registry = load_registry(args.state_path)

    if args.command == "set-targets":
        manifest = registry.set_targets(
            gold_target=args.gold_target,
            customer_pack_target=args.customer_pack_target,
        )
        _print_json(manifest.to_dict())
        return 0

    if args.command == "add-gold":
        record = registry.upsert_gold_case(
            case_id=args.case_id,
            title=args.title,
            domain=args.domain,
            jurisdiction=args.jurisdiction,
            framework=args.framework,
            control_id=args.control_id,
            status=args.status,
            notes=args.notes,
        )
        _print_json(record.__dict__)
        return 0

    if args.command == "add-pack":
        record = registry.upsert_customer_pack(
            pack_id=args.pack_id,
            customer_name=args.customer_name,
            domain=args.domain,
            jurisdiction=args.jurisdiction,
            framework=args.framework,
            status=args.status,
            notes=args.notes,
        )
        _print_json(record.__dict__)
        return 0

    if args.command == "set-discipline":
        if args.suite_green == args.suite_red:
            parser.error("exactly one of --suite-green or --suite-red must be provided")
        if args.suite_red and not args.failing_gate:
            parser.error("--suite-red requires at least one --failing-gate")
        discipline = registry.set_final_execution(
            suite_green=args.suite_green,
            failing_gate_names=args.failing_gate,
            ref=args.ref,
        )
        _print_json(discipline.__dict__)
        return 0

    if args.command == "summary":
        summary_obj = registry.write_readiness_outputs() if args.write else registry.summarize()
        _print_json(summary_obj.to_dict())
        if args.strict and not summary_obj.overall_ready:
            return 1
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
