from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


ROOT = Path.cwd()

DEFAULT_PLAN_JSON = ROOT / "config" / "proof_batch_real_002.plan.json"
DEFAULT_READINESS_JSON = ROOT / "logs" / "proof_density" / "proof_batch_real_002.readiness.json"
DEFAULT_BLOCKER_JSON = ROOT / "logs" / "proof_density" / "blocker_elimination" / "proof_batch_real_002" / "blocker_report.json"

DEFAULT_WORKSPACE_JSON = ROOT / "logs" / "proof_density" / "repair_acceleration" / "proof_batch_real_002.repair_workspace.json"
DEFAULT_WORKSPACE_MD = ROOT / "logs" / "proof_density" / "repair_acceleration" / "proof_batch_real_002.repair_workspace.md"

DEFAULT_VALIDATION_JSON = ROOT / "logs" / "proof_density" / "repair_acceleration" / "proof_batch_real_002.repair_workspace_validation.json"
DEFAULT_VALIDATION_MD = ROOT / "logs" / "proof_density" / "repair_acceleration" / "proof_batch_real_002.repair_workspace_validation.md"

DEFAULT_READY_MANIFEST = ROOT / "config" / "proof_batch_real_002.ready_only.json"


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    item_id: str
    code: str
    message: str


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


def parse_plan(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("plan must contain non-empty items list")
    out: list[dict[str, Any]] = []
    for row in items:
        if not isinstance(row, dict):
            raise ValueError("plan item must be object")
        item_id = normalize_slug(str(row.get("id", "")).strip())
        if not item_id:
            raise ValueError("plan item missing id")
        out.append(
            {
                "kind": str(row.get("kind", "")).strip(),
                "id": item_id,
                "title": str(row.get("title", "")).strip(),
                "source_dir": str(row.get("source_dir", "")).strip(),
                "domains": [normalize_slug(str(x)) for x in row.get("domains", [])],
                "jurisdictions": [normalize_slug(str(x)) for x in row.get("jurisdictions", [])],
                "reason": str(row.get("reason", "coverage_gap")).strip(),
            }
        )
    return out


def parse_readiness(path: Path) -> dict[str, dict[str, Any]]:
    payload = load_json(path)
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError("readiness must contain items list")
    out: dict[str, dict[str, Any]] = {}
    for row in items:
        if not isinstance(row, dict):
            raise ValueError("readiness item must be object")
        item_id = normalize_slug(str(row.get("id", "")).strip())
        if item_id:
            out[item_id] = row
    return out


def parse_blocker_report(path: Path) -> dict[str, dict[str, Any]]:
    payload = load_json(path)
    rows = payload.get("all_items")
    if not isinstance(rows, list):
        raise ValueError("blocker report must contain all_items list")
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("blocker report item must be object")
        item_id = normalize_slug(str(row.get("id", "")).strip())
        if item_id:
            out[item_id] = row
    return out


def build_workspace_entry(
    *,
    plan_item: dict[str, Any],
    readiness_item: dict[str, Any] | None,
    blocker_item: dict[str, Any] | None,
) -> dict[str, Any]:
    issues = blocker_item.get("issues", []) if isinstance(blocker_item, dict) else []
    missing_required = readiness_item.get("missing_required", []) if isinstance(readiness_item, dict) else []
    validation_errors = readiness_item.get("validation_errors", []) if isinstance(readiness_item, dict) else []
    placeholder_findings = readiness_item.get("placeholder_findings", []) if isinstance(readiness_item, dict) else []

    required_files = ["audit_context.json"]
    if plan_item["kind"] == "gold_case":
        required_files.extend(["expected_assertions.json", "case_notes.md"])

    entry = {
        "kind": plan_item["kind"],
        "id": plan_item["id"],
        "title": plan_item["title"],
        "source_dir": plan_item["source_dir"],
        "domains": plan_item["domains"],
        "jurisdictions": plan_item["jurisdictions"],
        "reason": plan_item["reason"],
        "status": "ready" if isinstance(readiness_item, dict) and readiness_item.get("ready") is True else "blocked",
        "required_files": required_files,
        "current_findings": {
            "missing_required": missing_required,
            "validation_errors": validation_errors,
            "placeholder_findings": placeholder_findings,
            "blocker_count": blocker_item.get("blocker_count") if isinstance(blocker_item, dict) else None,
            "blocker_score": blocker_item.get("blocker_score") if isinstance(blocker_item, dict) else None,
            "primary_blocker_type": blocker_item.get("primary_blocker_type") if isinstance(blocker_item, dict) else None,
            "issues": issues,
        },
        "operator_repair": {
            "completed": True if isinstance(readiness_item, dict) and readiness_item.get("ready") is True else False,
            "files_present": {},
            "audit_context_checked": False if plan_item["kind"] in {"gold_case", "customer_pack"} else True,
            "expected_assertions_checked": False if plan_item["kind"] == "gold_case" else True,
            "case_notes_checked": False if plan_item["kind"] == "gold_case" else True,
            "placeholders_removed": False if placeholder_findings else True,
            "repair_notes": "",
            "evidence_refs": [],
        },
    }
    for rel in required_files:
        entry["operator_repair"]["files_present"][rel] = False
    return entry


def build_workspace(
    *,
    plan_items: list[dict[str, Any]],
    readiness_map: dict[str, dict[str, Any]],
    blocker_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    entries = []
    for plan_item in plan_items:
        entries.append(
            build_workspace_entry(
                plan_item=plan_item,
                readiness_item=readiness_map.get(plan_item["id"]),
                blocker_item=blocker_map.get(plan_item["id"]),
            )
        )
    entries.sort(key=lambda row: (row["status"] != "blocked", row["kind"], row["id"]))
    return {
        "version": "v1",
        "generated_at_epoch": int(time.time()),
        "instructions": {
            "goal": "Turn blocked proof intake items into truly ready importable items without inventing anything.",
            "rules": [
                "real corpus only",
                "do not invent expected outcomes",
                "do not weaken deterministic truth",
                "do not let historical context override current truth",
                "remove placeholders completely",
                "mark completed=true only when the item is actually ready",
                "repair_notes must describe what changed and why",
                "evidence_refs must point to real source files or real case files",
            ],
        },
        "entries": entries,
    }


def render_workspace_md(workspace: dict[str, Any]) -> str:
    lines = [
        "# Proof Intake Repair Workspace",
        "",
        f"- generated_at_epoch: `{workspace['generated_at_epoch']}`",
        f"- entry_count: `{len(workspace['entries'])}`",
        "",
        "## Rules",
        "",
    ]
    for row in workspace["instructions"]["rules"]:
        lines.append(f"- {row}")
    lines.append("")
    for entry in workspace["entries"]:
        lines.extend(
            [
                f"## {entry['id']}",
                "",
                f"- status: `{entry['status']}`",
                f"- kind: `{entry['kind']}`",
                f"- source_dir: `{entry['source_dir']}`",
                f"- domains: `{entry['domains']}`",
                f"- jurisdictions: `{entry['jurisdictions']}`",
                f"- required_files: `{entry['required_files']}`",
                f"- missing_required: `{entry['current_findings']['missing_required']}`",
                f"- validation_errors: `{entry['current_findings']['validation_errors']}`",
                f"- placeholder_findings: `{entry['current_findings']['placeholder_findings']}`",
                f"- primary_blocker_type: `{entry['current_findings']['primary_blocker_type']}`",
                "",
                "Fill operator_repair in repair_workspace.json for this item.",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def validate_operator_repair(entry: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    item_id = str(entry.get("id", "")).strip()
    status = str(entry.get("status", "")).strip()
    repair = entry.get("operator_repair")
    if not isinstance(repair, dict):
        return [ValidationIssue("error", item_id, "repair.missing_operator_repair", "operator_repair must be object")]

    completed = repair.get("completed")
    if completed not in {True, False}:
        issues.append(ValidationIssue("error", item_id, "repair.invalid_completed", "completed must be boolean"))

    files_present = repair.get("files_present")
    if not isinstance(files_present, dict):
        issues.append(ValidationIssue("error", item_id, "repair.invalid_files_present", "files_present must be object"))
        files_present = {}

    for rel in entry.get("required_files", []):
        if files_present.get(rel) is not True:
            issues.append(ValidationIssue("error", item_id, "repair.required_file_not_confirmed", f"required file not confirmed: {rel}"))

    if repair.get("audit_context_checked") is not True:
        issues.append(ValidationIssue("error", item_id, "repair.audit_context_unchecked", "audit_context_checked must be true"))
    if entry.get("kind") == "gold_case" and repair.get("expected_assertions_checked") is not True:
        issues.append(ValidationIssue("error", item_id, "repair.expected_assertions_unchecked", "expected_assertions_checked must be true for gold cases"))
    if entry.get("kind") == "gold_case" and repair.get("case_notes_checked") is not True:
        issues.append(ValidationIssue("error", item_id, "repair.case_notes_unchecked", "case_notes_checked must be true for gold cases"))
    if repair.get("placeholders_removed") is not True:
        issues.append(ValidationIssue("error", item_id, "repair.placeholders_not_cleared", "placeholders_removed must be true"))

    repair_notes = str(repair.get("repair_notes", "")).strip()
    if not repair_notes:
        issues.append(ValidationIssue("error", item_id, "repair.missing_notes", "repair_notes must be non-empty"))
    elif len(repair_notes) < 20:
        issues.append(ValidationIssue("warning", item_id, "repair.short_notes", "repair_notes looks too short"))

    evidence_refs = repair.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not evidence_refs or not all(str(x).strip() for x in evidence_refs):
        issues.append(ValidationIssue("error", item_id, "repair.invalid_evidence_refs", "evidence_refs must be non-empty list of strings"))

    if status == "ready" and completed is not True:
        issues.append(ValidationIssue("warning", item_id, "repair.ready_item_not_marked_completed", "item is already ready but completed=false"))
    return issues


def validate_workspace(workspace: dict[str, Any]) -> dict[str, Any]:
    entries = workspace.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("workspace must contain non-empty entries list")

    issues: list[ValidationIssue] = []
    decided_ready = 0
    blocked = 0
    seen: set[str] = set()

    for entry in entries:
        if not isinstance(entry, dict):
            issues.append(ValidationIssue("error", ".", "workspace.entry_not_object", "workspace entry must be object"))
            continue
        item_id = str(entry.get("id", "")).strip()
        if not item_id:
            issues.append(ValidationIssue("error", ".", "workspace.missing_id", "workspace entry missing id"))
            continue
        if item_id in seen:
            issues.append(ValidationIssue("error", item_id, "workspace.duplicate_id", "duplicate item id"))
        seen.add(item_id)

        if str(entry.get("status", "")).strip() == "blocked":
            blocked += 1

        entry_issues = validate_operator_repair(entry)
        issues.extend(entry_issues)
        repair = entry.get("operator_repair", {})
        if isinstance(repair, dict) and repair.get("completed") is True and not any(issue.severity == "error" and issue.item_id == item_id for issue in entry_issues):
            decided_ready += 1

    return {
        "generated_at_epoch": int(time.time()),
        "entry_count": len(entries),
        "blocked_entry_count": blocked,
        "repair_ready_count": decided_ready,
        "issue_count": len(issues),
        "issues": [
            {
                "severity": issue.severity,
                "item_id": issue.item_id,
                "code": issue.code,
                "message": issue.message,
            }
            for issue in issues
        ],
    }


def render_validation_md(report: dict[str, Any]) -> str:
    lines = [
        "# Proof Intake Repair Workspace Validation",
        "",
        f"- entry_count: `{report['entry_count']}`",
        f"- blocked_entry_count: `{report['blocked_entry_count']}`",
        f"- repair_ready_count: `{report['repair_ready_count']}`",
        f"- issue_count: `{report['issue_count']}`",
        "",
    ]
    for issue in report["issues"]:
        lines.append(f"- [{issue['severity']}] `{issue['item_id']}` `{issue['code']}` - {issue['message']}")
    lines.append("")
    return "\n".join(lines)


def compile_ready_manifest(workspace: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for entry in workspace["entries"]:
        repair = entry["operator_repair"]
        if repair.get("completed") is not True:
            continue
        rows.append(
            {
                "kind": entry["kind"],
                "id": entry["id"],
                "title": entry["title"],
                "source_dir": entry["source_dir"],
                "domains": entry["domains"],
                "jurisdictions": entry["jurisdictions"],
            }
        )
    return {"items": rows}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Accelerate blocked proof intake repair into ready import manifests")
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init-workspace")
    init_parser.add_argument("--plan-json", default=str(DEFAULT_PLAN_JSON))
    init_parser.add_argument("--readiness-json", default=str(DEFAULT_READINESS_JSON))
    init_parser.add_argument("--blocker-json", default=str(DEFAULT_BLOCKER_JSON))
    init_parser.add_argument("--workspace-json", default=str(DEFAULT_WORKSPACE_JSON))
    init_parser.add_argument("--workspace-md", default=str(DEFAULT_WORKSPACE_MD))

    validate_parser = sub.add_parser("validate-workspace")
    validate_parser.add_argument("--workspace-json", default=str(DEFAULT_WORKSPACE_JSON))
    validate_parser.add_argument("--validation-json", default=str(DEFAULT_VALIDATION_JSON))
    validate_parser.add_argument("--validation-md", default=str(DEFAULT_VALIDATION_MD))
    validate_parser.add_argument("--strict", action="store_true")

    compile_parser = sub.add_parser("compile-ready-manifest")
    compile_parser.add_argument("--workspace-json", default=str(DEFAULT_WORKSPACE_JSON))
    compile_parser.add_argument("--validation-json", default=str(DEFAULT_VALIDATION_JSON))
    compile_parser.add_argument("--validation-md", default=str(DEFAULT_VALIDATION_MD))
    compile_parser.add_argument("--ready-manifest", default=str(DEFAULT_READY_MANIFEST))
    compile_parser.add_argument("--strict", action="store_true")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "init-workspace":
        plan_items = parse_plan(Path(args.plan_json))
        readiness_map = parse_readiness(Path(args.readiness_json))
        blocker_map = parse_blocker_report(Path(args.blocker_json))
        workspace = build_workspace(plan_items=plan_items, readiness_map=readiness_map, blocker_map=blocker_map)
        atomic_write_json(Path(args.workspace_json), workspace)
        atomic_write_text(Path(args.workspace_md), render_workspace_md(workspace))
        print(json.dumps({
            "workspace_json": str(Path(args.workspace_json)),
            "workspace_md": str(Path(args.workspace_md)),
            "entry_count": len(workspace["entries"]),
        }, indent=2))
        return 0

    if args.command == "validate-workspace":
        workspace = load_json(Path(args.workspace_json))
        report = validate_workspace(workspace)
        atomic_write_json(Path(args.validation_json), report)
        atomic_write_text(Path(args.validation_md), render_validation_md(report))
        print(json.dumps({
            "entry_count": report["entry_count"],
            "blocked_entry_count": report["blocked_entry_count"],
            "repair_ready_count": report["repair_ready_count"],
            "issue_count": report["issue_count"],
            "validation_json": str(Path(args.validation_json)),
            "validation_md": str(Path(args.validation_md)),
        }, indent=2))
        if args.strict and report["issue_count"] > 0:
            return 1
        return 0

    if args.command == "compile-ready-manifest":
        workspace = load_json(Path(args.workspace_json))
        report = validate_workspace(workspace)
        atomic_write_json(Path(args.validation_json), report)
        atomic_write_text(Path(args.validation_md), render_validation_md(report))
        if args.strict and report["issue_count"] > 0:
            print(json.dumps({
                "compiled": False,
                "reason": "workspace validation failed",
                "issue_count": report["issue_count"],
                "validation_json": str(Path(args.validation_json)),
                "validation_md": str(Path(args.validation_md)),
            }, indent=2))
            return 1
        manifest = compile_ready_manifest(workspace)
        atomic_write_json(Path(args.ready_manifest), manifest)
        print(json.dumps({
            "compiled": True,
            "ready_item_count": len(manifest["items"]),
            "ready_manifest": str(Path(args.ready_manifest)),
            "validation_json": str(Path(args.validation_json)),
            "validation_md": str(Path(args.validation_md)),
        }, indent=2))
        return 0

    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
