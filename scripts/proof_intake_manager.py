from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


ROOT = Path.cwd()
DEFAULT_PLAN_JSON = ROOT / "config" / "proof_batch_real_002.plan.json"
DEFAULT_READINESS_JSON = ROOT / "logs" / "proof_density" / "proof_batch_real_002.readiness.json"
DEFAULT_READINESS_MD = ROOT / "logs" / "proof_density" / "proof_batch_real_002.readiness.md"
DEFAULT_BATCH_MANIFEST = ROOT / "config" / "proof_batch_real_002.json"

PLACEHOLDER_MARKERS = [
    "todo",
    "tbd",
    "placeholder",
    "lorem ipsum",
    "dummy data",
    "fake data",
    "mock data",
    "example only",
    "replace me",
    "fill me",
]

REQUIRED_BY_KIND = {
    "gold_case": [
        "audit_context.json",
        "expected_assertions.json",
        "case_notes.md",
    ],
    "customer_pack": [
        "audit_context.json",
    ],
}

OPTIONAL_BY_KIND = {
    "gold_case": [
        "evidence_index.json",
        "source_manifest.json",
        "notes.md",
    ],
    "customer_pack": [
        "evidence_index.json",
        "source_manifest.json",
        "notes.md",
    ],
}

REQUIRED_AUDIT_CONTEXT_FIELDS = {
    "audit_id",
    "entity_name",
    "audit_type",
    "industry",
    "jurisdictions",
    "source_families",
    "query_terms",
    "top_k",
}


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=False) + "\n")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_slug(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("&", "and")
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )


def safe_rel_path(value: str) -> Path:
    p = Path(value)
    if p.is_absolute():
        raise ValueError(f"Expected relative path, got absolute path: {value}")
    if ".." in p.parts:
        raise ValueError(f"Parent traversal not allowed: {value}")
    return p


@dataclass(frozen=True)
class PlannedItem:
    kind: str
    item_id: str
    title: str
    source_dir: str
    domains: list[str]
    jurisdictions: list[str]
    reason: str


def parse_plan(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing plan json: {path}")
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("Plan must be a JSON object")
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("Plan must contain a non-empty items list")
    return payload


def planned_items_from_plan(plan: dict[str, Any]) -> list[PlannedItem]:
    out: list[PlannedItem] = []
    for idx, raw in enumerate(plan["items"]):
        if not isinstance(raw, dict):
            raise ValueError(f"Plan item {idx} must be an object")

        kind = str(raw.get("kind", "")).strip()
        item_id = normalize_slug(str(raw.get("id", "")).strip())
        title = str(raw.get("title", "")).strip()
        source_dir = str(raw.get("source_dir", "")).strip()
        domains = raw.get("domains")
        jurisdictions = raw.get("jurisdictions")
        reason = str(raw.get("reason", "coverage_gap")).strip()

        if kind not in {"gold_case", "customer_pack"}:
            raise ValueError(f"Invalid kind for plan item {idx}: {kind}")
        if not item_id:
            raise ValueError(f"Missing id for plan item {idx}")
        if not title:
            raise ValueError(f"Missing title for plan item {idx}")
        if not source_dir:
            raise ValueError(f"Missing source_dir for plan item {idx}")
        safe_rel_path(source_dir)

        if not isinstance(domains, list) or not domains:
            raise ValueError(f"Missing domains for plan item {idx}")
        if not isinstance(jurisdictions, list) or not jurisdictions:
            raise ValueError(f"Missing jurisdictions for plan item {idx}")

        out.append(
            PlannedItem(
                kind=kind,
                item_id=item_id,
                title=title,
                source_dir=source_dir,
                domains=[normalize_slug(str(x)) for x in domains],
                jurisdictions=[normalize_slug(str(x)) for x in jurisdictions],
                reason=reason,
            )
        )
    return out


def build_audit_context_template(item: PlannedItem) -> dict[str, Any]:
    title_slug = normalize_slug(item.title)
    return {
        "audit_id": item.item_id,
        "entity_name": item.title,
        "audit_type": "",
        "industry": "",
        "jurisdictions": item.jurisdictions,
        "entity_type": "",
        "products": [],
        "customer_types": [],
        "domains": item.domains,
        "source_families": [],
        "query_terms": [],
        "top_k": 5,
        "notes": "",
        "historical_context_is_non_authoritative": True,
        "deterministic_current_audit_truth_only": True,
        "operator_fill_status": {
            "real_sources_attached": False,
            "placeholder_free": False,
            "ready_for_import": False
        },
        "intake_identity_hint": title_slug,
    }


def build_expected_assertions_template(item: PlannedItem) -> dict[str, Any]:
    return {
        "case_id": item.item_id,
        "expected": {
            "equals": {},
            "contains": {},
            "minimums": {}
        },
        "rules": {
            "no_invented_pass_outcome": True,
            "deterministic_current_truth_only": True,
            "historical_context_cannot_override_current_truth": True
        }
    }


def build_case_notes_template(item: PlannedItem) -> str:
    return (
        f"# {item.item_id}\n\n"
        f"- title: {item.title}\n"
        f"- kind: {item.kind}\n"
        f"- domains: {', '.join(item.domains)}\n"
        f"- jurisdictions: {', '.join(item.jurisdictions)}\n"
        f"- reason: {item.reason}\n\n"
        "## Real Source Requirements\n\n"
        "- describe the real corpus used\n"
        "- cite source artifacts by exact filename/path\n"
        "- do not paste placeholders\n"
        "- do not invent outcomes\n"
        "- align assertions to deterministic audit truth only\n"
    )


def build_notes_template(item: PlannedItem) -> str:
    return (
        f"# Intake Notes: {item.item_id}\n\n"
        "Use this file for operator notes only.\n"
        "Do not use placeholder text.\n"
        "Do not state expected pass/fail unless grounded in real source material.\n"
    )


def build_readme(item: PlannedItem) -> str:
    required = REQUIRED_BY_KIND[item.kind]
    optional = OPTIONAL_BY_KIND[item.kind]
    lines = [
        f"# Intake Workspace: {item.item_id}",
        "",
        f"- title: `{item.title}`",
        f"- kind: `{item.kind}`",
        f"- domains: `{', '.join(item.domains)}`",
        f"- jurisdictions: `{', '.join(item.jurisdictions)}`",
        f"- reason: `{item.reason}`",
        "",
        "## Required files",
        "",
    ]
    for rel in required:
        lines.append(f"- `{rel}`")
    lines.extend(["", "## Optional files", ""])
    for rel in optional:
        lines.append(f"- `{rel}`")
    lines.extend([
        "",
        "## Rules",
        "",
        "- real corpus only",
        "- no placeholders",
        "- no invented outcomes",
        "- deterministic current audit truth remains authoritative",
        "- historical context must never override current truth",
        "",
        "## Ready criteria",
        "",
        "- all required files exist",
        "- audit_context.json matches the strict importer contract",
        "- expected_assertions.json matches the strict gold-case contract",
        "- no placeholder markers in text/json/md files",
        "- source_families and query_terms are real and non-empty",
        "",
    ])
    return "\n".join(lines) + "\n"


def ensure_text_file(path: Path, content: str, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        return
    atomic_write_text(path, content)


def ensure_json_file(path: Path, payload: dict[str, Any], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        return
    atomic_write_json(path, payload)


def materialize_workspace(item: PlannedItem, overwrite: bool) -> dict[str, Any]:
    source_dir = ROOT / safe_rel_path(item.source_dir)
    source_dir.mkdir(parents=True, exist_ok=True)

    ensure_text_file(source_dir / "README.md", build_readme(item), overwrite=overwrite)
    ensure_json_file(source_dir / "audit_context.json", build_audit_context_template(item), overwrite=overwrite)
    ensure_text_file(source_dir / "notes.md", build_notes_template(item), overwrite=overwrite)

    if item.kind == "gold_case":
        ensure_json_file(source_dir / "expected_assertions.json", build_expected_assertions_template(item), overwrite=overwrite)
        ensure_text_file(source_dir / "case_notes.md", build_case_notes_template(item), overwrite=overwrite)

    return {
        "id": item.item_id,
        "kind": item.kind,
        "source_dir": str(source_dir.relative_to(ROOT)),
        "materialized": True,
    }


def scan_placeholder_markers(path: Path) -> list[str]:
    findings: list[str] = []
    if not path.exists():
        return findings
    scan_suffixes = {".json", ".md", ".txt", ".yaml", ".yml"}
    for file_path in sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in scan_suffixes):
        text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
        for marker in PLACEHOLDER_MARKERS:
            if marker in text:
                findings.append(f"{file_path.relative_to(path)}::{marker}")
                break
    return findings


def nonempty_json_object(path: Path) -> tuple[bool, str | None]:
    if not path.exists():
        return False, "missing"
    try:
        payload = load_json(path)
    except Exception as exc:
        return False, f"invalid_json:{exc}"
    if not isinstance(payload, dict):
        return False, "not_object"
    if not payload:
        return False, "empty_object"
    return True, None


def validate_audit_context(path: Path, item: PlannedItem) -> list[str]:
    errors: list[str] = []
    ok, reason = nonempty_json_object(path)
    if not ok:
        errors.append(f"audit_context.json::{reason}")
        return errors

    payload = load_json(path)
    missing_fields = sorted(REQUIRED_AUDIT_CONTEXT_FIELDS - set(payload.keys()))
    if missing_fields:
        errors.append(f"audit_context.json::missing_fields={missing_fields}")

    for field in ["audit_id", "entity_name", "audit_type", "industry"]:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"audit_context.json::empty_{field}")

    source_families = payload.get("source_families")
    query_terms = payload.get("query_terms")
    top_k = payload.get("top_k")
    domains = payload.get("domains")
    jurisdictions = payload.get("jurisdictions")

    if not isinstance(source_families, list) or not source_families:
        errors.append("audit_context.json::missing_source_families")
    if not isinstance(query_terms, list) or not query_terms:
        errors.append("audit_context.json::missing_query_terms")
    if not isinstance(top_k, int) or top_k <= 0:
        errors.append("audit_context.json::invalid_top_k")
    if not isinstance(domains, list) or not domains:
        errors.append("audit_context.json::missing_domains")
    if not isinstance(jurisdictions, list) or not jurisdictions:
        errors.append("audit_context.json::missing_jurisdictions")

    if isinstance(domains, list):
        norm_domains = [normalize_slug(str(x)) for x in domains]
        if norm_domains != item.domains:
            errors.append(f"audit_context.json::domains_mismatch expected={item.domains} actual={norm_domains}")

    if isinstance(jurisdictions, list):
        norm_jur = [normalize_slug(str(x)) for x in jurisdictions]
        if norm_jur != item.jurisdictions:
            errors.append(f"audit_context.json::jurisdictions_mismatch expected={item.jurisdictions} actual={norm_jur}")

    if normalize_slug(str(payload.get("audit_id", ""))) != item.item_id:
        errors.append(f"audit_context.json::audit_id_mismatch expected={item.item_id}")

    return errors


def validate_expected_assertions(path: Path, item: PlannedItem) -> list[str]:
    errors: list[str] = []
    ok, reason = nonempty_json_object(path)
    if not ok:
        errors.append(f"expected_assertions.json::{reason}")
        return errors

    payload = load_json(path)
    case_id = normalize_slug(str(payload.get("case_id", "") or ""))
    if case_id != item.item_id:
        errors.append(f"expected_assertions.json::case_id_mismatch expected={item.item_id} actual={case_id}")

    expected = payload.get("expected")
    if not isinstance(expected, dict):
        errors.append("expected_assertions.json::missing_expected")
        return errors

    equals = expected.get("equals")
    contains = expected.get("contains")
    minimums = expected.get("minimums")
    if not isinstance(equals, dict):
        errors.append("expected_assertions.json::equals_not_object")
    if not isinstance(contains, dict):
        errors.append("expected_assertions.json::contains_not_object")
    if not isinstance(minimums, dict):
        errors.append("expected_assertions.json::minimums_not_object")

    if isinstance(equals, dict) and isinstance(contains, dict) and isinstance(minimums, dict):
        if not any([equals, contains, minimums]):
            errors.append("expected_assertions.json::no_meaningful_expected_values")

    return errors


def compute_item_readiness(item: PlannedItem) -> dict[str, Any]:
    source_dir = ROOT / safe_rel_path(item.source_dir)
    required = REQUIRED_BY_KIND[item.kind]
    optional = OPTIONAL_BY_KIND[item.kind]

    file_presence = {}
    missing_required: list[str] = []
    present_required = 0

    for rel in required:
        exists = (source_dir / rel).exists()
        file_presence[rel] = exists
        if exists:
            present_required += 1
        else:
            missing_required.append(rel)

    for rel in optional:
        file_presence[rel] = (source_dir / rel).exists()

    validation_errors: list[str] = []
    validation_errors.extend(validate_audit_context(source_dir / "audit_context.json", item))

    if item.kind == "gold_case":
        validation_errors.extend(validate_expected_assertions(source_dir / "expected_assertions.json", item))

    placeholders = scan_placeholder_markers(source_dir)

    required_ratio = present_required / len(required)
    score = 0.0
    score += required_ratio * 0.6
    score += 0.2 if not validation_errors else 0.0
    score += 0.2 if not placeholders else 0.0
    score = round(score, 3)

    ready = (not missing_required) and (not validation_errors) and (not placeholders)

    return {
        "kind": item.kind,
        "id": item.item_id,
        "title": item.title,
        "source_dir": str(source_dir.relative_to(ROOT)),
        "domains": item.domains,
        "jurisdictions": item.jurisdictions,
        "reason": item.reason,
        "required_files": required,
        "optional_files": optional,
        "file_presence": file_presence,
        "missing_required": missing_required,
        "validation_errors": validation_errors,
        "placeholder_findings": placeholders,
        "readiness_score": score,
        "ready": ready,
    }


def build_batch_manifest_from_ready_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    manifest_items = []
    for row in items:
        manifest_items.append(
            {
                "kind": row["kind"],
                "id": row["id"],
                "title": row["title"],
                "source_dir": row["source_dir"],
                "domains": row["domains"],
                "jurisdictions": row["jurisdictions"],
            }
        )
    return {"items": manifest_items}


def render_readiness_markdown(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Batch Readiness: {summary['batch_label']}")
    lines.append("")
    lines.append(f"- generated_at_epoch: `{summary['generated_at_epoch']}`")
    lines.append(f"- total_items: `{summary['counts']['total_items']}`")
    lines.append(f"- ready_items: `{summary['counts']['ready_items']}`")
    lines.append(f"- blocked_items: `{summary['counts']['blocked_items']}`")
    lines.append(f"- ready_ratio: `{summary['counts']['ready_ratio']}`")
    lines.append("")
    lines.append("## Items")
    lines.append("")
    for item in summary["items"]:
        lines.append(f"### {item['id']}")
        lines.append(f"- kind: `{item['kind']}`")
        lines.append(f"- ready: `{item['ready']}`")
        lines.append(f"- readiness_score: `{item['readiness_score']}`")
        if item["missing_required"]:
            lines.append(f"- missing_required: `{item['missing_required']}`")
        if item["validation_errors"]:
            lines.append(f"- validation_errors: `{item['validation_errors']}`")
        if item["placeholder_findings"]:
            lines.append(f"- placeholder_findings: `{item['placeholder_findings']}`")
        lines.append("")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize and validate strict proof-batch intake workspaces")
    sub = parser.add_subparsers(dest="command", required=True)

    p_materialize = sub.add_parser("materialize")
    p_materialize.add_argument("--plan-json", default=str(DEFAULT_PLAN_JSON))
    p_materialize.add_argument("--overwrite", action="store_true")

    p_validate = sub.add_parser("validate")
    p_validate.add_argument("--plan-json", default=str(DEFAULT_PLAN_JSON))
    p_validate.add_argument("--readiness-json", default=str(DEFAULT_READINESS_JSON))
    p_validate.add_argument("--readiness-md", default=str(DEFAULT_READINESS_MD))
    p_validate.add_argument("--batch-manifest", default=str(DEFAULT_BATCH_MANIFEST))
    p_validate.add_argument("--strict", action="store_true")

    return parser.parse_args()


def do_materialize(plan_json: Path, overwrite: bool) -> int:
    plan = parse_plan(plan_json)
    items = planned_items_from_plan(plan)
    results = [materialize_workspace(item, overwrite=overwrite) for item in items]
    print(json.dumps({
        "batch_label": plan.get("batch_label"),
        "materialized_count": len(results),
        "items": results,
    }, indent=2))
    return 0


def do_validate(plan_json: Path, readiness_json: Path, readiness_md: Path, batch_manifest: Path, strict: bool) -> int:
    plan = parse_plan(plan_json)
    items = planned_items_from_plan(plan)
    computed = [compute_item_readiness(item) for item in items]
    ready_items = [x for x in computed if x["ready"]]
    blocked_items = [x for x in computed if not x["ready"]]

    summary = {
        "version": "v1",
        "generated_at_epoch": int(time.time()),
        "batch_label": plan.get("batch_label"),
        "counts": {
            "total_items": len(computed),
            "ready_items": len(ready_items),
            "blocked_items": len(blocked_items),
            "ready_ratio": round((len(ready_items) / len(computed)) if computed else 0.0, 3),
        },
        "items": computed,
        "ready_batch_manifest_path": str(batch_manifest),
    }

    atomic_write_json(readiness_json, summary)
    atomic_write_text(readiness_md, render_readiness_markdown(summary))
    atomic_write_json(batch_manifest, build_batch_manifest_from_ready_items(ready_items))

    print(json.dumps({
        "batch_label": summary["batch_label"],
        "readiness_json": str(readiness_json),
        "readiness_md": str(readiness_md),
        "batch_manifest": str(batch_manifest),
        "total_items": summary["counts"]["total_items"],
        "ready_items": summary["counts"]["ready_items"],
        "blocked_items": summary["counts"]["blocked_items"],
        "ready_ids": [x["id"] for x in ready_items],
        "blocked_ids": [x["id"] for x in blocked_items],
    }, indent=2))

    if strict and blocked_items:
        return 1
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "materialize":
        return do_materialize(Path(args.plan_json), overwrite=bool(args.overwrite))
    if args.command == "validate":
        return do_validate(
            Path(args.plan_json),
            Path(args.readiness_json),
            Path(args.readiness_md),
            Path(args.batch_manifest),
            bool(args.strict),
        )
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
