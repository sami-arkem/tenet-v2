from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


ROOT = Path.cwd()

DEFAULT_PLAN_JSON = ROOT / "config" / "proof_batch_real_002.plan.json"
DEFAULT_READINESS_JSON = ROOT / "logs" / "proof_density" / "proof_batch_real_002.readiness.json"
DEFAULT_OUTPUT_DIR = ROOT / "logs" / "proof_density" / "blocker_elimination" / "proof_batch_real_002"
DEFAULT_READY_MANIFEST = ROOT / "config" / "proof_batch_real_002.ready_only.json"

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

VALID_EXPECTED_ROOT_KEYS = {"case_id", "expected", "rules"}
PATH_KEY_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


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
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"Absolute path not allowed: {value}")
    if ".." in path.parts:
        raise ValueError(f"Parent traversal not allowed: {value}")
    return path


@dataclass(frozen=True)
class PlanItem:
    kind: str
    item_id: str
    title: str
    source_dir: str
    domains: list[str]
    jurisdictions: list[str]
    reason: str


@dataclass(frozen=True)
class ReadinessItem:
    kind: str
    item_id: str
    title: str
    source_dir: str
    domains: list[str]
    jurisdictions: list[str]
    reason: str
    ready: bool
    readiness_score: float
    missing_required: list[str]
    validation_errors: list[str]
    placeholder_findings: list[str]


def parse_plan(path: Path) -> tuple[str, list[PlanItem]]:
    payload = load_json(path)
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError(f"Plan missing items: {path}")
    out: list[PlanItem] = []
    for idx, raw in enumerate(items):
        if not isinstance(raw, dict):
            raise ValueError(f"Plan item {idx} must be object")
        out.append(
            PlanItem(
                kind=str(raw["kind"]).strip(),
                item_id=normalize_slug(str(raw["id"]).strip()),
                title=str(raw["title"]).strip(),
                source_dir=str(raw["source_dir"]).strip(),
                domains=[normalize_slug(str(x)) for x in raw.get("domains", [])],
                jurisdictions=[normalize_slug(str(x)) for x in raw.get("jurisdictions", [])],
                reason=str(raw.get("reason", "coverage_gap")).strip(),
            )
        )
    return str(payload.get("batch_label", "proof_batch")).strip(), out


def parse_readiness(path: Path) -> tuple[str, list[ReadinessItem]]:
    payload = load_json(path)
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError(f"Readiness missing items: {path}")
    out: list[ReadinessItem] = []
    for idx, raw in enumerate(items):
        if not isinstance(raw, dict):
            raise ValueError(f"Readiness item {idx} must be object")
        out.append(
            ReadinessItem(
                kind=str(raw["kind"]).strip(),
                item_id=normalize_slug(str(raw["id"]).strip()),
                title=str(raw["title"]).strip(),
                source_dir=str(raw["source_dir"]).strip(),
                domains=[normalize_slug(str(x)) for x in raw.get("domains", [])],
                jurisdictions=[normalize_slug(str(x)) for x in raw.get("jurisdictions", [])],
                reason=str(raw.get("reason", "coverage_gap")).strip(),
                ready=bool(raw.get("ready", False)),
                readiness_score=float(raw.get("readiness_score", 0.0)),
                missing_required=[str(x) for x in raw.get("missing_required", [])],
                validation_errors=[str(x) for x in raw.get("validation_errors", [])],
                placeholder_findings=[str(x) for x in raw.get("placeholder_findings", [])],
            )
        )
    return str(payload.get("batch_label", "proof_batch")).strip(), out


def read_text_if_exists(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="ignore")


def json_object_or_error(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        payload = load_json(path)
    except Exception as exc:
        return None, f"invalid_json:{exc}"
    if not isinstance(payload, dict):
        return None, "not_object"
    if not payload:
        return None, "empty_object"
    return payload, None


def _nonempty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(x, str) and x.strip() for x in value)


def scan_placeholders(root: Path) -> list[str]:
    findings: list[str] = []
    if not root.exists():
        return findings
    suffixes = {".json", ".md", ".txt", ".yaml", ".yml"}
    for file_path in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in suffixes):
        text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
        for marker in PLACEHOLDER_MARKERS:
            if marker in text:
                findings.append(f"{file_path.relative_to(root)}::{marker}")
                break
    return findings


def validate_audit_context_semantics(*, path: Path, plan_item: PlanItem) -> list[str]:
    payload, reason = json_object_or_error(path)
    if payload is None:
        return [f"audit_context.json::{reason}"]

    errors: list[str] = []
    missing_fields = sorted(REQUIRED_AUDIT_CONTEXT_FIELDS - set(payload.keys()))
    if missing_fields:
        errors.append(f"audit_context.json::missing_fields={missing_fields}")

    for field in ["audit_id", "entity_name", "audit_type", "industry"]:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"audit_context.json::empty_{field}")

    if normalize_slug(str(payload.get("audit_id", ""))) != plan_item.item_id:
        errors.append(f"audit_context.json::audit_id_mismatch expected={plan_item.item_id}")

    entity_name = payload.get("entity_name")
    if isinstance(entity_name, str) and entity_name.strip() and entity_name.strip() != plan_item.title:
        errors.append(f"audit_context.json::entity_name_mismatch expected={plan_item.title}")

    domains = payload.get("domains")
    jurisdictions = payload.get("jurisdictions")
    if not _nonempty_string_list(domains):
        errors.append("audit_context.json::missing_domains")
    else:
        norm_domains = [normalize_slug(str(x)) for x in domains]
        if norm_domains != plan_item.domains:
            errors.append(f"audit_context.json::domains_mismatch expected={plan_item.domains} actual={norm_domains}")

    if not _nonempty_string_list(jurisdictions):
        errors.append("audit_context.json::missing_jurisdictions")
    else:
        norm_jur = [normalize_slug(str(x)) for x in jurisdictions]
        if norm_jur != plan_item.jurisdictions:
            errors.append(f"audit_context.json::jurisdictions_mismatch expected={plan_item.jurisdictions} actual={norm_jur}")

    source_families = payload.get("source_families")
    if not _nonempty_string_list(source_families):
        errors.append("audit_context.json::missing_source_families")

    query_terms = payload.get("query_terms")
    if not _nonempty_string_list(query_terms):
        errors.append("audit_context.json::missing_query_terms")

    top_k = payload.get("top_k")
    if not isinstance(top_k, int) or top_k <= 0:
        errors.append("audit_context.json::invalid_top_k")

    if payload.get("historical_context_is_non_authoritative") is not True:
        errors.append("audit_context.json::historical_context_is_non_authoritative_must_be_true")
    if payload.get("deterministic_current_audit_truth_only") is not True:
        errors.append("audit_context.json::deterministic_current_audit_truth_only_must_be_true")

    operator_fill_status = payload.get("operator_fill_status")
    if not isinstance(operator_fill_status, dict):
        errors.append("audit_context.json::missing_operator_fill_status")
    else:
        for key in ["real_sources_attached", "placeholder_free", "ready_for_import"]:
            if operator_fill_status.get(key) is not True:
                errors.append(f"audit_context.json::operator_fill_status_{key}_must_be_true")

    return errors


def _validate_expected_mapping(name: str, value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return [f"expected_assertions.json::{name}_not_object"]
    for raw_key, raw_value in value.items():
        key = str(raw_key).strip()
        if not key or not PATH_KEY_RE.fullmatch(key):
            errors.append(f"expected_assertions.json::{name}_invalid_key:{raw_key}")
        if name == "equals":
            if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
                errors.append(f"expected_assertions.json::{name}_empty_value:{raw_key}")
        elif name == "contains":
            if isinstance(raw_value, list):
                if not raw_value or not all(isinstance(x, str) and x.strip() for x in raw_value):
                    errors.append(f"expected_assertions.json::{name}_invalid_list:{raw_key}")
            elif isinstance(raw_value, str):
                if not raw_value.strip():
                    errors.append(f"expected_assertions.json::{name}_empty_value:{raw_key}")
            else:
                errors.append(f"expected_assertions.json::{name}_invalid_value:{raw_key}")
        elif name == "minimums":
            if not isinstance(raw_value, (int, float)):
                errors.append(f"expected_assertions.json::{name}_invalid_numeric:{raw_key}")
    return errors


def validate_expected_assertions_semantics(*, path: Path, plan_item: PlanItem) -> list[str]:
    payload, reason = json_object_or_error(path)
    if payload is None:
        return [f"expected_assertions.json::{reason}"]

    errors: list[str] = []
    case_id = normalize_slug(str(payload.get("case_id", "") or ""))
    if case_id != plan_item.item_id:
        errors.append(f"expected_assertions.json::case_id_mismatch expected={plan_item.item_id} actual={case_id}")

    unexpected_keys = sorted(set(payload.keys()) - VALID_EXPECTED_ROOT_KEYS)
    if unexpected_keys:
        errors.append(f"expected_assertions.json::unexpected_keys={unexpected_keys}")

    rules = payload.get("rules")
    if not isinstance(rules, dict):
        errors.append("expected_assertions.json::missing_rules")
    else:
        if rules.get("no_invented_pass_outcome") is not True:
            errors.append("expected_assertions.json::no_invented_pass_outcome_must_be_true")
        if rules.get("deterministic_current_truth_only") is not True:
            errors.append("expected_assertions.json::deterministic_current_truth_only_must_be_true")
        if rules.get("historical_context_cannot_override_current_truth") is not True:
            errors.append("expected_assertions.json::historical_context_cannot_override_current_truth_must_be_true")

    expected = payload.get("expected")
    if not isinstance(expected, dict):
        return errors + ["expected_assertions.json::missing_expected"]

    equals = expected.get("equals", {})
    contains = expected.get("contains", {})
    minimums = expected.get("minimums", {})
    errors.extend(_validate_expected_mapping("equals", equals))
    errors.extend(_validate_expected_mapping("contains", contains))
    errors.extend(_validate_expected_mapping("minimums", minimums))

    if isinstance(equals, dict) and isinstance(contains, dict) and isinstance(minimums, dict):
        if not any([equals, contains, minimums]):
            errors.append("expected_assertions.json::no_meaningful_expected_values")

    return errors


def classify_issue(issue: str) -> str:
    if "missing required file" in issue or "missing_fields" in issue or "::missing_" in issue:
        return "missing_required"
    if "placeholder" in issue:
        return "placeholder"
    if "mismatch" in issue:
        return "taxonomy_or_identity_mismatch"
    if "invalid_json" in issue or "not_object" in issue or "unexpected_keys" in issue:
        return "invalid_json_or_shape"
    if "expected_assertions.json" in issue:
        return "assertions_semantics"
    if "audit_context.json" in issue:
        return "audit_context_semantics"
    return "other"


def blocker_weight(issue_type: str) -> int:
    return {
        "missing_required": 100,
        "invalid_json_or_shape": 90,
        "taxonomy_or_identity_mismatch": 80,
        "audit_context_semantics": 70,
        "assertions_semantics": 70,
        "placeholder": 60,
        "other": 50,
    }.get(issue_type, 10)


def build_fix_hint(issue: str, kind: str) -> str:
    if "empty_audit_type" in issue:
        return "set audit_type to the real audit type used by Tenet for this corpus-backed item"
    if "empty_industry" in issue:
        return "set industry to the real industry under audit"
    if "empty_entity_name" in issue or "entity_name_mismatch" in issue:
        return "align entity_name to the planned item title for the real audited entity"
    if "audit_id_mismatch" in issue:
        return "set audit_id to the planned item id exactly"
    if "missing_source_families" in issue:
        return "add one or more real source_families grounded in the corpus"
    if "missing_query_terms" in issue:
        return "add real retrieval query_terms grounded in the corpus"
    if "invalid_top_k" in issue:
        return "set top_k to a positive integer that matches normal retrieval usage"
    if "domains_mismatch" in issue or "jurisdictions_mismatch" in issue:
        return "align domains and jurisdictions to the batch plan; do not move the plan to fit bad intake"
    if "historical_context_is_non_authoritative_must_be_true" in issue:
        return "set historical_context_is_non_authoritative to true"
    if "deterministic_current_audit_truth_only_must_be_true" in issue:
        return "set deterministic_current_audit_truth_only to true"
    if "operator_fill_status" in issue:
        return "set operator_fill_status flags to true only after real sources are attached and placeholders are removed"
    if "case_id_mismatch" in issue:
        return "set case_id to the planned gold-case id exactly"
    if "missing_rules" in issue:
        return "add rules with all three truth-preserving booleans set to true"
    if "_must_be_true" in issue:
        return "set the truth-preserving rule flag to true"
    if "no_meaningful_expected_values" in issue:
        return "add real expected.equals, expected.contains, or expected.minimums values from observed deterministic output"
    if "equals_" in issue or "contains_" in issue or "minimums_" in issue:
        return "repair expected assertion keys and values so they are non-empty and type-correct"
    if "missing required file" in issue:
        return "create the missing required file with real content only"
    if "placeholder" in issue:
        return "remove placeholder text and replace it with real intake content"
    if kind == "gold_case":
        return "repair the gold case so it matches the strict importer contract and deterministic eval contract"
    return "repair the customer pack so it matches the strict evidence-pack importer contract"


def item_issue_file_body(
    *,
    batch_label: str,
    plan_item: PlanItem,
    readiness_item: ReadinessItem | None,
    issues: list[dict[str, Any]],
) -> str:
    lines = [
        f"# Repair File: {plan_item.item_id}",
        "",
        f"- batch_label: `{batch_label}`",
        f"- kind: `{plan_item.kind}`",
        f"- title: `{plan_item.title}`",
        f"- source_dir: `{plan_item.source_dir}`",
        f"- domains: `{', '.join(plan_item.domains)}`",
        f"- jurisdictions: `{', '.join(plan_item.jurisdictions)}`",
        f"- reason: `{plan_item.reason}`",
    ]
    if readiness_item is not None:
        lines.extend([
            f"- current_ready: `{readiness_item.ready}`",
            f"- current_readiness_score: `{readiness_item.readiness_score}`",
        ])
    lines.extend(["", "## Repair Actions", ""])
    if not issues:
        lines.append("- no issues")
    else:
        for idx, issue in enumerate(issues, start=1):
            lines.append(f"{idx}. [{issue['issue_type']}] {issue['message']}")
            lines.append(f"   - fix: {issue['fix_hint']}")
    lines.extend([
        "",
        "## Non-negotiables",
        "",
        "- real corpus only",
        "- do not invent pass outcomes",
        "- deterministic current audit truth is authoritative",
        "- historical context must never override current truth",
        "- do not weaken the importer contract or gates",
        "",
    ])
    return "\n".join(lines)


def validate_item(*, plan_item: PlanItem, readiness_item: ReadinessItem | None) -> dict[str, Any]:
    source_dir = ROOT / safe_rel_path(plan_item.source_dir)
    issues: list[dict[str, Any]] = []

    if readiness_item is None:
        issues.append(
            {
                "issue_type": "missing_required",
                "message": "item missing from readiness ledger",
                "fix_hint": "refresh readiness so the plan and ledger are aligned",
            }
        )
    else:
        for rel in readiness_item.missing_required:
            issues.append(
                {
                    "issue_type": "missing_required",
                    "message": f"missing required file: {rel}",
                    "fix_hint": "create the missing required file with real content only",
                }
            )
        for msg in readiness_item.validation_errors:
            issues.append(
                {
                    "issue_type": classify_issue(msg),
                    "message": msg,
                    "fix_hint": build_fix_hint(msg, plan_item.kind),
                }
            )
        for msg in readiness_item.placeholder_findings:
            issues.append(
                {
                    "issue_type": "placeholder",
                    "message": msg,
                    "fix_hint": "remove placeholder text and replace it with real intake content",
                }
            )

    for msg in validate_audit_context_semantics(path=source_dir / "audit_context.json", plan_item=plan_item):
        issues.append(
            {
                "issue_type": classify_issue(msg),
                "message": msg,
                "fix_hint": build_fix_hint(msg, plan_item.kind),
            }
        )

    if plan_item.kind == "gold_case":
        for msg in validate_expected_assertions_semantics(path=source_dir / "expected_assertions.json", plan_item=plan_item):
            issues.append(
                {
                    "issue_type": classify_issue(msg),
                    "message": msg,
                    "fix_hint": build_fix_hint(msg, plan_item.kind),
                }
            )
        case_notes = source_dir / "case_notes.md"
        if not case_notes.exists():
            issues.append(
                {
                    "issue_type": "missing_required",
                    "message": "missing required file: case_notes.md",
                    "fix_hint": "add case_notes.md with real source-grounded notes",
                }
            )
        else:
            text = read_text_if_exists(case_notes) or ""
            if not text.strip():
                issues.append(
                    {
                        "issue_type": "missing_required",
                        "message": "case_notes.md is empty",
                        "fix_hint": "add real source-grounded notes",
                    }
                )

    for msg in scan_placeholders(source_dir):
        issues.append(
            {
                "issue_type": "placeholder",
                "message": msg,
                "fix_hint": "remove placeholder text and replace it with real intake content",
            }
        )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for issue in issues:
        key = (issue["issue_type"], issue["message"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)

    blocker_counts = Counter(issue["issue_type"] for issue in deduped)
    primary_blocker_type = None
    blocker_score = 0
    if deduped:
        ranked = sorted(blocker_counts.items(), key=lambda item: (-blocker_weight(item[0]), -item[1], item[0]))
        primary_blocker_type = ranked[0][0]
        blocker_score = sum(blocker_weight(issue["issue_type"]) for issue in deduped)

    return {
        "kind": plan_item.kind,
        "id": plan_item.item_id,
        "title": plan_item.title,
        "source_dir": plan_item.source_dir,
        "domains": plan_item.domains,
        "jurisdictions": plan_item.jurisdictions,
        "reason": plan_item.reason,
        "ready": not deduped,
        "blocker_count": len(deduped),
        "blocker_score": blocker_score,
        "primary_blocker_type": primary_blocker_type,
        "issues": deduped,
    }


def ready_only_manifest(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "items": [
            {
                "kind": item["kind"],
                "id": item["id"],
                "title": item["title"],
                "source_dir": item["source_dir"],
                "domains": item["domains"],
                "jurisdictions": item["jurisdictions"],
            }
            for item in items
            if item["ready"]
        ]
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Proof Blocker Elimination Report: {report['batch_label']}",
        "",
        f"- generated_at_epoch: `{report['generated_at_epoch']}`",
        f"- total_items: `{report['counts']['total_items']}`",
        f"- ready_items: `{report['counts']['ready_items']}`",
        f"- blocked_items: `{report['counts']['blocked_items']}`",
        f"- ready_ratio: `{report['counts']['ready_ratio']}`",
        "",
        "## Blocker Type Counts",
        "",
    ]
    for key, value in report["blocker_type_counts"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Ranked Blocked Items", ""])
    for row in report["ranked_blocked_items"]:
        lines.append(f"### {row['id']}")
        lines.append(f"- kind: `{row['kind']}`")
        lines.append(f"- blocker_score: `{row['blocker_score']}`")
        lines.append(f"- blocker_count: `{row['blocker_count']}`")
        lines.append(f"- primary_blocker_type: `{row['primary_blocker_type']}`")
        lines.append(f"- source_dir: `{row['source_dir']}`")
        lines.append("- blockers:")
        for issue in row["issues"]:
            lines.append(f"  - `{issue['issue_type']}` :: `{issue['message']}` :: `{issue['fix_hint']}`")
        lines.append("")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Strict blocker elimination for proof-batch intake")
    parser.add_argument("--plan-json", default=str(DEFAULT_PLAN_JSON))
    parser.add_argument("--readiness-json", default=str(DEFAULT_READINESS_JSON))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--ready-manifest", default=str(DEFAULT_READY_MANIFEST))
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    batch_label_plan, plan_items = parse_plan(Path(args.plan_json))
    batch_label_readiness, readiness_items = parse_readiness(Path(args.readiness_json))
    if batch_label_plan != batch_label_readiness:
        raise ValueError(f"Batch label mismatch plan={batch_label_plan} readiness={batch_label_readiness}")

    readiness_map = {item.item_id: item for item in readiness_items}
    output_dir = Path(args.output_dir)
    repair_dir = output_dir / "repair_files"
    repair_dir.mkdir(parents=True, exist_ok=True)

    report_items: list[dict[str, Any]] = []
    blocker_type_counts: Counter[str] = Counter()

    for plan_item in plan_items:
        readiness_item = readiness_map.get(plan_item.item_id)
        result = validate_item(plan_item=plan_item, readiness_item=readiness_item)
        report_items.append(result)
        if not result["ready"]:
            for issue in result["issues"]:
                blocker_type_counts[issue["issue_type"]] += 1
        atomic_write_text(
            repair_dir / f"{plan_item.item_id}.md",
            item_issue_file_body(
                batch_label=batch_label_plan,
                plan_item=plan_item,
                readiness_item=readiness_item,
                issues=result["issues"],
            ),
        )

    ranked_blocked_items = sorted(
        [row for row in report_items if not row["ready"]],
        key=lambda row: (-row["blocker_score"], -row["blocker_count"], row["id"]),
    )
    ready_count = sum(1 for row in report_items if row["ready"])
    blocked_count = len(report_items) - ready_count
    report = {
        "version": "v1",
        "generated_at_epoch": int(time.time()),
        "batch_label": batch_label_plan,
        "counts": {
            "total_items": len(report_items),
            "ready_items": ready_count,
            "blocked_items": blocked_count,
            "ready_ratio": round((ready_count / len(report_items)) if report_items else 0.0, 3),
        },
        "blocker_type_counts": dict(sorted(blocker_type_counts.items())),
        "ranked_blocked_items": ranked_blocked_items,
        "all_items": report_items,
        "repair_dir": str(repair_dir),
        "ready_manifest_path": str(Path(args.ready_manifest)),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(output_dir / "blocker_report.json", report)
    atomic_write_text(output_dir / "blocker_report.md", render_markdown(report))
    atomic_write_json(Path(args.ready_manifest), ready_only_manifest(report_items))

    summary = {
        "batch_label": batch_label_plan,
        "ready_items": ready_count,
        "blocked_items": blocked_count,
        "ready_manifest_path": str(Path(args.ready_manifest)),
        "blocker_report_json": str(output_dir / "blocker_report.json"),
        "blocker_report_md": str(output_dir / "blocker_report.md"),
        "repair_dir": str(repair_dir),
        "top_blocker_types": dict(sorted(blocker_type_counts.items(), key=lambda item: (-item[1], item[0]))[:10]),
        "top_blocked_ids": [row["id"] for row in ranked_blocked_items[:10]],
    }
    print(json.dumps(summary, indent=2))
    if args.strict and blocked_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
