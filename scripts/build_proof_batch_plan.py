from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
DEFAULT_STATUS_PATH = ROOT / "logs" / "proof_density" / "proof_density_status.json"
DEFAULT_OUTPUT_JSON = ROOT / "config" / "proof_batch_real_002.plan.json"
DEFAULT_OUTPUT_MD = ROOT / "logs" / "proof_density" / "proof_batch_real_002.plan.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        Path(tmp_name).replace(path)
    finally:
        tmp_path = Path(tmp_name)
        if tmp_path.exists():
            tmp_path.unlink()


def normalize_slug(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("&", "and")
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )


def validate_batch_label(value: str) -> str:
    value = normalize_slug(value)
    if not re.fullmatch(r"[a-z0-9_]+", value):
        raise ValueError(f"Invalid batch label: {value}")
    return value


@dataclass(frozen=True)
class PlannedItem:
    kind: str
    item_id: str
    title: str
    source_dir: str
    domains: list[str]
    jurisdictions: list[str]
    reason: str


def next_sequence_for_prefix(root: Path, prefix: str) -> int:
    max_seen = 0
    if not root.exists():
        return 1
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)$")
    for child in root.iterdir():
        if not child.is_dir():
            continue
        match = pattern.match(child.name)
        if not match:
            continue
        max_seen = max(max_seen, int(match.group(1)))
    return max_seen + 1


def build_gold_id(domain: str, jurisdiction: str, ordinal: int) -> str:
    return f"{domain}_{jurisdiction}_case_{ordinal:03d}"


def build_pack_id(domain: str, jurisdiction: str, ordinal: int) -> str:
    return f"{domain}_{jurisdiction}_pack_{ordinal:03d}"


def titleize_slug(value: str) -> str:
    parts = value.split("_")
    return " ".join(part.upper() if len(part) <= 3 else part.capitalize() for part in parts)


def read_recommendations(status: dict[str, Any], branch_key: str, limit: int) -> list[dict[str, Any]]:
    recs = (
        status.get(branch_key, {})
        .get("gap_plan", {})
        .get("recommended_next_batch", [])
    )
    if not isinstance(recs, list):
        return []
    return recs[:limit]


def build_plan(
    *,
    status: dict[str, Any],
    batch_label: str,
    gold_limit: int,
    pack_limit: int,
    intake_root: Path,
    gold_root: Path,
    pack_root: Path,
) -> dict[str, Any]:
    gold_recs = read_recommendations(status, "gold_cases", gold_limit)
    pack_recs = read_recommendations(status, "customer_packs", pack_limit)

    planned_items: list[PlannedItem] = []
    intake_root_rel = intake_root.relative_to(ROOT)

    for rec in gold_recs:
        domain = normalize_slug(rec["domain"])
        jurisdiction = normalize_slug(rec["jurisdiction"])
        prefix = f"{domain}_{jurisdiction}_case"
        ordinal = next_sequence_for_prefix(gold_root, prefix)
        item_id = build_gold_id(domain, jurisdiction, ordinal)
        planned_items.append(
            PlannedItem(
                kind="gold_case",
                item_id=item_id,
                title=f"{titleize_slug(domain)} {titleize_slug(jurisdiction)} case {ordinal:03d}",
                source_dir=str(intake_root_rel / batch_label / item_id),
                domains=[domain],
                jurisdictions=[jurisdiction],
                reason=str(rec.get("reason", "coverage_gap")),
            )
        )

    for rec in pack_recs:
        domain = normalize_slug(rec["domain"])
        jurisdiction = normalize_slug(rec["jurisdiction"])
        prefix = f"{domain}_{jurisdiction}_pack"
        ordinal = next_sequence_for_prefix(pack_root, prefix)
        item_id = build_pack_id(domain, jurisdiction, ordinal)
        planned_items.append(
            PlannedItem(
                kind="customer_pack",
                item_id=item_id,
                title=f"{titleize_slug(domain)} {titleize_slug(jurisdiction)} pack {ordinal:03d}",
                source_dir=str(intake_root_rel / batch_label / item_id),
                domains=[domain],
                jurisdictions=[jurisdiction],
                reason=str(rec.get("reason", "coverage_gap")),
            )
        )

    gold_count = sum(1 for x in planned_items if x.kind == "gold_case")
    pack_count = sum(1 for x in planned_items if x.kind == "customer_pack")

    return {
        "version": "v1",
        "generated_at_epoch": int(time.time()),
        "batch_label": batch_label,
        "status_source": str(DEFAULT_STATUS_PATH),
        "rules": {
            "real_corpus_only": True,
            "no_placeholder_content": True,
            "no_invented_expected_outcomes": True,
            "historical_context_not_authoritative": True,
            "deterministic_core_authoritative": True
        },
        "counts": {
            "gold_cases_planned": gold_count,
            "customer_packs_planned": pack_count,
            "total_items_planned": len(planned_items)
        },
        "items": [
            {
                "kind": item.kind,
                "id": item.item_id,
                "title": item.title,
                "source_dir": item.source_dir,
                "domains": item.domains,
                "jurisdictions": item.jurisdictions,
                "reason": item.reason
            }
            for item in planned_items
        ]
    }


def render_markdown(plan: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Proof Batch Plan: {plan['batch_label']}")
    lines.append("")
    lines.append(f"- generated_at_epoch: `{plan['generated_at_epoch']}`")
    lines.append(f"- gold_cases_planned: `{plan['counts']['gold_cases_planned']}`")
    lines.append(f"- customer_packs_planned: `{plan['counts']['customer_packs_planned']}`")
    lines.append(f"- total_items_planned: `{plan['counts']['total_items_planned']}`")
    lines.append("")
    lines.append("## Intake Rules")
    lines.append("")
    lines.append("- real corpus only")
    lines.append("- no placeholders")
    lines.append("- no invented outcomes")
    lines.append("- deterministic current audit truth remains authoritative")
    lines.append("- do not let historical context override current truth")
    lines.append("")
    lines.append("## Planned Items")
    lines.append("")
    for item in plan["items"]:
        lines.append(f"### {item['id']}")
        lines.append(f"- kind: `{item['kind']}`")
        lines.append(f"- title: `{item['title']}`")
        lines.append(f"- domains: `{', '.join(item['domains'])}`")
        lines.append(f"- jurisdictions: `{', '.join(item['jurisdictions'])}`")
        lines.append(f"- reason: `{item['reason']}`")
        lines.append(f"- source_dir: `{item['source_dir']}`")
        lines.append("- required source files:")
        lines.append("  - `audit_context.json`")
        if item["kind"] == "gold_case":
            lines.append("  - `expected_assertions.json`")
            lines.append("  - `case_notes.md`")
        lines.append("- optional but preferred:")
        lines.append("  - `evidence_index.json`")
        lines.append("  - `source_manifest.json`")
        lines.append("  - `notes.md`")
        lines.append("")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the next strict proof batch plan from observed proof-density gaps")
    parser.add_argument("--status-json", default=str(DEFAULT_STATUS_PATH))
    parser.add_argument("--batch-label", default="proof_batch_real_002")
    parser.add_argument("--gold-limit", type=int, default=8)
    parser.add_argument("--pack-limit", type=int, default=3)
    parser.add_argument("--intake-root", default="intake")
    parser.add_argument("--gold-root", default="evals/gold_cases")
    parser.add_argument("--pack-root", default="data/customer_evidence_packs")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    status_path = Path(args.status_json)
    if not status_path.exists():
        raise FileNotFoundError(f"Missing proof density status: {status_path}")

    batch_label = validate_batch_label(args.batch_label)
    status = load_json(status_path)

    intake_root = ROOT / args.intake_root
    gold_root = ROOT / args.gold_root
    pack_root = ROOT / args.pack_root

    plan = build_plan(
        status=status,
        batch_label=batch_label,
        gold_limit=int(args.gold_limit),
        pack_limit=int(args.pack_limit),
        intake_root=intake_root,
        gold_root=gold_root,
        pack_root=pack_root,
    )

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)

    atomic_write(output_json, json.dumps(plan, indent=2) + "\n")
    atomic_write(output_md, render_markdown(plan))

    print(json.dumps({
        "batch_label": plan["batch_label"],
        "gold_cases_planned": plan["counts"]["gold_cases_planned"],
        "customer_packs_planned": plan["counts"]["customer_packs_planned"],
        "output_json": str(output_json),
        "output_md": str(output_md),
        "planned_ids": [item["id"] for item in plan["items"]]
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
