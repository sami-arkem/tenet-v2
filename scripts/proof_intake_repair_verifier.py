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

DEFAULT_WORKSPACE_JSON = ROOT / "logs" / "proof_density" / "repair_acceleration" / "proof_batch_real_002.repair_workspace.json"
DEFAULT_REPORT_JSON = ROOT / "logs" / "proof_density" / "repair_acceleration" / "proof_batch_real_002.repair_verification.json"
DEFAULT_REPORT_MD = ROOT / "logs" / "proof_density" / "repair_acceleration" / "proof_batch_real_002.repair_verification.md"
DEFAULT_VERIFIED_MANIFEST = ROOT / "config" / "proof_batch_real_002.verified_ready_only.json"

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

TEXT_EXTENSIONS = {".json", ".md", ".txt", ".yaml", ".yml"}

ALLOWED_ASSERTION_TYPES = {
    "finding",
    "gap",
    "missing_evidence",
    "coverage",
    "decision",
}

CONTROL_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")
REGIME_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")
ASSERTION_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")


@dataclass(frozen=True)
class Issue:
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


def safe_rel_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"absolute path not allowed: {value}")
    if ".." in path.parts:
        raise ValueError(f"parent traversal not allowed: {value}")
    return path


def read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = load_json(path)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _normalize_tokens(values: list[Any]) -> list[str]:
    return [str(x).strip().lower().replace("-", "_").replace(" ", "_") for x in values]


def scan_placeholders(root: Path) -> list[str]:
    findings: list[str] = []
    patterns = []
    for marker in PLACEHOLDER_MARKERS:
        if re.fullmatch(r"[a-z ]+", marker):
            patterns.append((marker, re.compile(rf"(?<![a-z0-9_]){re.escape(marker)}(?![a-z0-9_])")))
        else:
            patterns.append((marker, re.compile(re.escape(marker))))
    for file_path in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_EXTENSIONS):
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
        except Exception:
            continue
        for marker, pattern in patterns:
            if pattern.search(text):
                findings.append(f"{file_path.relative_to(root)}::{marker}")
                break
    return findings


def validate_audit_context(path: Path, expected_domains: list[str], expected_jurisdictions: list[str]) -> list[str]:
    issues: list[str] = []
    payload = read_json_if_exists(path)
    if payload is None:
        return ["audit_context.invalid_or_missing"]

    if payload.get("historical_context_is_non_authoritative") is not True:
        issues.append("audit_context.historical_context_is_non_authoritative_not_true")
    if payload.get("deterministic_current_audit_truth_only") is not True:
        issues.append("audit_context.deterministic_current_audit_truth_only_not_true")

    entity_name = payload.get("entity_name")
    audit_type = payload.get("audit_type")
    industry = payload.get("industry")
    source_families = payload.get("source_families")
    query_terms = payload.get("query_terms")
    top_k = payload.get("top_k")

    if not isinstance(entity_name, str) or not entity_name.strip():
        issues.append("audit_context.missing_entity_name")
    if not isinstance(audit_type, str) or not audit_type.strip():
        issues.append("audit_context.missing_audit_type")
    if not isinstance(industry, str) or not industry.strip():
        issues.append("audit_context.missing_industry")
    if not isinstance(source_families, list) or not source_families or not all(str(x).strip() for x in source_families):
        issues.append("audit_context.missing_or_invalid_source_families")
    if not isinstance(query_terms, list) or not query_terms or not all(str(x).strip() for x in query_terms):
        issues.append("audit_context.missing_or_invalid_query_terms")
    if not isinstance(top_k, int) or top_k <= 0:
        issues.append("audit_context.invalid_top_k")

    domains = payload.get("domains")
    jurisdictions = payload.get("jurisdictions")
    if not isinstance(domains, list) or not domains:
        issues.append("audit_context.missing_domains")
    else:
        norm_domains = _normalize_tokens(domains)
        if norm_domains != expected_domains:
            issues.append(f"audit_context.domains_mismatch expected={expected_domains} actual={norm_domains}")

    if not isinstance(jurisdictions, list) or not jurisdictions:
        issues.append("audit_context.missing_jurisdictions")
    else:
        norm_jurisdictions = _normalize_tokens(jurisdictions)
        if norm_jurisdictions != expected_jurisdictions:
            issues.append(f"audit_context.jurisdictions_mismatch expected={expected_jurisdictions} actual={norm_jurisdictions}")

    operator_fill_status = payload.get("operator_fill_status")
    if not isinstance(operator_fill_status, dict):
        issues.append("audit_context.missing_operator_fill_status")
    else:
        for key in ["real_sources_attached", "placeholder_free", "ready_for_import"]:
            if operator_fill_status.get(key) is not True:
                issues.append(f"audit_context.operator_fill_status_{key}_not_true")

    return issues


def validate_expected_assertions(path: Path) -> list[str]:
    issues: list[str] = []
    payload = read_json_if_exists(path)
    if payload is None:
        return ["expected_assertions.invalid_or_missing"]

    rules = payload.get("rules")
    if not isinstance(rules, dict):
        issues.append("expected_assertions.missing_rules")
    else:
        if rules.get("no_invented_pass_outcome") is not True:
            issues.append("expected_assertions.rule_no_invented_pass_outcome_not_true")
        if rules.get("deterministic_current_truth_only") is not True:
            issues.append("expected_assertions.rule_deterministic_current_truth_only_not_true")
        if rules.get("historical_context_cannot_override_current_truth") is not True:
            issues.append("expected_assertions.rule_historical_context_cannot_override_current_truth_not_true")

    expected = payload.get("expected")
    if isinstance(expected, dict):
        equals = expected.get("equals", {})
        contains = expected.get("contains", {})
        minimums = expected.get("minimums", {})
        if not isinstance(equals, dict):
            issues.append("expected_assertions.expected_equals_not_object")
        if not isinstance(contains, dict):
            issues.append("expected_assertions.expected_contains_not_object")
        if not isinstance(minimums, dict):
            issues.append("expected_assertions.expected_minimums_not_object")
        if isinstance(equals, dict) and isinstance(contains, dict) and isinstance(minimums, dict) and not any([equals, contains, minimums]):
            issues.append("expected_assertions.no_meaningful_expected_values")
        return issues

    assertions = payload.get("expected_assertions")
    if not isinstance(assertions, list) or not assertions:
        issues.append("expected_assertions.missing_entries")
        return issues

    meaningful = 0
    for idx, row in enumerate(assertions):
        prefix = f"expected_assertions.row_{idx}"
        if not isinstance(row, dict):
            issues.append(f"{prefix}.not_object")
            continue

        assertion_id = row.get("assertion_id")
        row_type = row.get("type")
        expected_value = row.get("expected_value")
        evidence_refs = row.get("evidence_refs")
        control_id = row.get("control_id")
        regime_id = row.get("regime_id")

        if not isinstance(assertion_id, str) or not assertion_id.strip():
            issues.append(f"{prefix}.missing_assertion_id")
        elif not ASSERTION_ID_RE.fullmatch(assertion_id.strip()):
            issues.append(f"{prefix}.invalid_assertion_id")

        if not isinstance(row_type, str) or row_type not in ALLOWED_ASSERTION_TYPES:
            issues.append(f"{prefix}.invalid_type:{row_type}")

        if not isinstance(expected_value, str) or not expected_value.strip():
            issues.append(f"{prefix}.missing_expected_value")
        else:
            meaningful += 1

        if not isinstance(evidence_refs, list) or not evidence_refs or not all(str(x).strip() for x in evidence_refs):
            issues.append(f"{prefix}.missing_or_invalid_evidence_refs")

        if control_id not in (None, "") and (not isinstance(control_id, str) or not CONTROL_ID_RE.fullmatch(control_id.strip())):
            issues.append(f"{prefix}.invalid_control_id")
        if regime_id not in (None, "") and (not isinstance(regime_id, str) or not REGIME_ID_RE.fullmatch(regime_id.strip())):
            issues.append(f"{prefix}.invalid_regime_id")

    if meaningful == 0:
        issues.append("expected_assertions.no_meaningful_expected_values")
    return issues


def validate_case_notes(path: Path) -> list[str]:
    if not path.exists():
        return ["case_notes.missing"]
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ["case_notes.unreadable"]
    if not text.strip():
        return ["case_notes.empty"]
    if len(text.strip()) < 40:
        return ["case_notes.too_short"]
    return []


def validate_operator_claims(entry: dict[str, Any], source_dir: Path) -> list[str]:
    issues: list[str] = []
    repair = entry.get("operator_repair", {})
    files_present = repair.get("files_present", {}) if isinstance(repair, dict) else {}

    for rel in entry.get("required_files", []):
        exists = (source_dir / rel).exists()
        if files_present.get(rel) is True and not exists:
            issues.append(f"operator_claims.file_marked_present_but_missing:{rel}")
        if files_present.get(rel) is not True and exists:
            issues.append(f"operator_claims.file_exists_but_not_confirmed:{rel}")

    if repair.get("placeholders_removed") is True:
        placeholders = scan_placeholders(source_dir)
        if placeholders:
            issues.append("operator_claims.placeholders_marked_removed_but_still_present")

    evidence_refs = repair.get("evidence_refs")
    if isinstance(evidence_refs, list):
        for idx, value in enumerate(evidence_refs):
            if not str(value).strip():
                issues.append(f"operator_claims.blank_evidence_ref:{idx}")

    return issues


def verify_entry(entry: dict[str, Any]) -> dict[str, Any]:
    item_id = str(entry.get("id", "")).strip()
    kind = str(entry.get("kind", "")).strip()
    source_dir = ROOT / safe_rel_path(str(entry.get("source_dir", "")).strip())
    expected_domains = [str(x).strip().lower() for x in entry.get("domains", [])]
    expected_jurisdictions = [str(x).strip().lower() for x in entry.get("jurisdictions", [])]

    issues: list[Issue] = []
    actual_checks: dict[str, Any] = {
        "source_dir_exists": source_dir.exists(),
        "required_files_present": {},
        "placeholders": [],
        "audit_context_issues": [],
        "expected_assertions_issues": [],
        "case_notes_issues": [],
        "operator_claim_mismatches": [],
    }

    if not source_dir.exists():
        issues.append(Issue("error", item_id, "source_dir.missing", f"source_dir missing: {source_dir}"))
        return {
            "id": item_id,
            "kind": kind,
            "verified_ready": False,
            "issue_count": len(issues),
            "issues": [issue.__dict__ for issue in issues],
            "actual_checks": actual_checks,
        }

    for rel in entry.get("required_files", []):
        exists = (source_dir / rel).exists()
        actual_checks["required_files_present"][rel] = exists
        if not exists:
            issues.append(Issue("error", item_id, "required_file.missing", f"missing required file: {rel}"))

    placeholders = scan_placeholders(source_dir)
    actual_checks["placeholders"] = placeholders
    for value in placeholders:
        issues.append(Issue("error", item_id, "content.placeholder_present", value))

    audit_context_issues = validate_audit_context(source_dir / "audit_context.json", expected_domains, expected_jurisdictions)
    actual_checks["audit_context_issues"] = audit_context_issues
    for value in audit_context_issues:
        issues.append(Issue("error", item_id, "audit_context.invalid", value))

    if kind == "gold_case":
        expected_assertions_issues = validate_expected_assertions(source_dir / "expected_assertions.json")
        actual_checks["expected_assertions_issues"] = expected_assertions_issues
        for value in expected_assertions_issues:
            issues.append(Issue("error", item_id, "expected_assertions.invalid", value))

        case_notes_issues = validate_case_notes(source_dir / "case_notes.md")
        actual_checks["case_notes_issues"] = case_notes_issues
        for value in case_notes_issues:
            issues.append(Issue("error", item_id, "case_notes.invalid", value))

    operator_claim_mismatches = validate_operator_claims(entry, source_dir)
    actual_checks["operator_claim_mismatches"] = operator_claim_mismatches
    for value in operator_claim_mismatches:
        issues.append(Issue("warning", item_id, "operator_claims.mismatch", value))

    repair = entry.get("operator_repair", {})
    completed = repair.get("completed") is True if isinstance(repair, dict) else False
    if completed is not True:
        issues.append(Issue("warning", item_id, "operator_repair.not_completed", "operator_repair.completed is not true"))

    verified_ready = completed and not any(issue.severity == "error" for issue in issues)
    return {
        "id": item_id,
        "kind": kind,
        "title": entry.get("title"),
        "source_dir": entry.get("source_dir"),
        "domains": entry.get("domains"),
        "jurisdictions": entry.get("jurisdictions"),
        "verified_ready": verified_ready,
        "issue_count": len(issues),
        "issues": [issue.__dict__ for issue in issues],
        "actual_checks": actual_checks,
    }


def build_report(workspace: dict[str, Any]) -> dict[str, Any]:
    entries = workspace.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("workspace must contain non-empty entries")
    verified_entries = [verify_entry(entry) for entry in entries]
    ready_count = sum(1 for row in verified_entries if row["verified_ready"])
    blocked_count = len(verified_entries) - ready_count
    error_count = 0
    warning_count = 0
    for row in verified_entries:
        for issue in row["issues"]:
            if issue["severity"] == "error":
                error_count += 1
            elif issue["severity"] == "warning":
                warning_count += 1
    return {
        "generated_at_epoch": int(time.time()),
        "entry_count": len(verified_entries),
        "verified_ready_count": ready_count,
        "verified_blocked_count": blocked_count,
        "error_count": error_count,
        "warning_count": warning_count,
        "entries": verified_entries,
    }


def render_report_md(report: dict[str, Any]) -> str:
    lines = [
        "# Proof Intake Repair Verification",
        "",
        f"- entry_count: `{report['entry_count']}`",
        f"- verified_ready_count: `{report['verified_ready_count']}`",
        f"- verified_blocked_count: `{report['verified_blocked_count']}`",
        f"- error_count: `{report['error_count']}`",
        f"- warning_count: `{report['warning_count']}`",
        "",
    ]
    for row in report["entries"]:
        lines.append(f"## {row['id']}")
        lines.append("")
        lines.append(f"- verified_ready: `{row['verified_ready']}`")
        lines.append(f"- issue_count: `{row['issue_count']}`")
        if row["issues"]:
            lines.append("- issues:")
            for issue in row["issues"]:
                lines.append(f"  - [{issue['severity']}] `{issue['code']}` - {issue['message']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def compile_verified_manifest(report: dict[str, Any]) -> dict[str, Any]:
    items = []
    for row in report["entries"]:
        if not row["verified_ready"]:
            continue
        items.append(
            {
                "kind": row["kind"],
                "id": row["id"],
                "title": row["title"],
                "source_dir": row["source_dir"],
                "domains": row["domains"],
                "jurisdictions": row["jurisdictions"],
            }
        )
    return {"items": items}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministically verify repaired proof intake items against actual filesystem state")
    parser.add_argument("--workspace-json", default=str(DEFAULT_WORKSPACE_JSON))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    parser.add_argument("--verified-manifest", default=str(DEFAULT_VERIFIED_MANIFEST))
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = load_json(Path(args.workspace_json))
    report = build_report(workspace)
    atomic_write_json(Path(args.report_json), report)
    atomic_write_text(Path(args.report_md), render_report_md(report))

    manifest = compile_verified_manifest(report)
    atomic_write_json(Path(args.verified_manifest), manifest)

    print(json.dumps({
        "entry_count": report["entry_count"],
        "verified_ready_count": report["verified_ready_count"],
        "verified_blocked_count": report["verified_blocked_count"],
        "error_count": report["error_count"],
        "warning_count": report["warning_count"],
        "verified_manifest": str(Path(args.verified_manifest)),
        "report_json": str(Path(args.report_json)),
        "report_md": str(Path(args.report_md)),
    }, indent=2))

    if args.strict and report["verified_blocked_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
