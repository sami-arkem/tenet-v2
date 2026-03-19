from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


ROOT = Path.cwd()

DEFAULT_WORKSPACE_JSON = ROOT / "logs" / "proof_density" / "repair_acceleration" / "proof_batch_real_002.repair_workspace.json"
DEFAULT_REPORT_JSON = ROOT / "logs" / "proof_density" / "repair_acceleration" / "proof_batch_real_002.safe_autofix_report.json"
DEFAULT_REPORT_MD = ROOT / "logs" / "proof_density" / "repair_acceleration" / "proof_batch_real_002.safe_autofix_report.md"
DEFAULT_BACKUP_ROOT = ROOT / "logs" / "proof_density" / "repair_acceleration" / "safe_autofix_backups"
DEFAULT_WORKSPACE_BACKUP = ROOT / "logs" / "proof_density" / "repair_acceleration" / "proof_batch_real_002.repair_workspace.before_safe_autofix.json"

VERIFIER_SCRIPT = ROOT / "scripts" / "proof_intake_repair_verifier.py"

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

SAFE_AUDIT_CONTEXT_DEFAULTS = {
    "historical_context_is_non_authoritative": True,
    "deterministic_current_audit_truth_only": True,
}

SAFE_EXPECTED_ASSERTION_RULES = {
    "no_invented_pass_outcome": True,
    "deterministic_current_truth_only": True,
    "historical_context_cannot_override_current_truth": True,
}


@dataclass(frozen=True)
class FileMutation:
    path: str
    changed: bool
    reason: str


@dataclass(frozen=True)
class ItemResult:
    item_id: str
    kind: str
    source_dir: str
    changed: bool
    blocked: bool
    backup_dir: str | None
    mutations: list[FileMutation]
    reasons: list[str]


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


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def normalize_slug(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("&", "and")
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )


def read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = load_json(path)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def ensure_backup(source_dir: Path, backup_root: Path) -> Path:
    backup_root.mkdir(parents=True, exist_ok=True)
    dest = backup_root / source_dir.name
    suffix = 1
    while dest.exists():
        dest = backup_root / f"{source_dir.name}_{suffix:03d}"
        suffix += 1
    shutil.copytree(source_dir, dest)
    return dest


def json_changed(before_obj: dict[str, Any], after_obj: dict[str, Any]) -> bool:
    return json.dumps(before_obj, sort_keys=True) != json.dumps(after_obj, sort_keys=True)


def scan_placeholders(root: Path) -> list[str]:
    findings: list[str] = []
    patterns = []
    for marker in PLACEHOLDER_MARKERS:
        if all(ch.islower() or ch == " " for ch in marker):
            patterns.append((marker, rf"(?<![a-z0-9_]){marker.replace(' ', r'\ ')}(?![a-z0-9_])"))
        else:
            patterns.append((marker, marker))
    import re

    compiled = [(marker, re.compile(pattern)) for marker, pattern in patterns]
    for file_path in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_EXTENSIONS):
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
        except Exception:
            continue
        for marker, pattern in compiled:
            if pattern.search(text):
                findings.append(f"{file_path.relative_to(root)}::{marker}")
                break
    return findings


def _normalize_tokens(values: list[Any]) -> list[str]:
    return [normalize_slug(str(value)) for value in values]


def patch_audit_context(
    *,
    payload: dict[str, Any],
    expected_domains: list[str],
    expected_jurisdictions: list[str],
    placeholders_present: bool,
) -> tuple[dict[str, Any], list[str], bool]:
    out = dict(payload)
    reasons: list[str] = []
    blocked = False

    for key, value in SAFE_AUDIT_CONTEXT_DEFAULTS.items():
        if out.get(key) is not True:
            out[key] = value
            reasons.append(f"set {key}=true")

    if not isinstance(out.get("domains"), list) or not out.get("domains"):
        out["domains"] = expected_domains
        reasons.append(f"filled domains from batch plan: {expected_domains}")

    if not isinstance(out.get("jurisdictions"), list) or not out.get("jurisdictions"):
        out["jurisdictions"] = expected_jurisdictions
        reasons.append(f"filled jurisdictions from batch plan: {expected_jurisdictions}")

    for field in ("entity_name", "audit_type", "industry", "notes"):
        if isinstance(out.get(field), str):
            trimmed = out[field].strip()
            if trimmed != out[field]:
                out[field] = trimmed
                reasons.append(f"trimmed whitespace in {field}")

    operator_fill_status = out.get("operator_fill_status")
    if not isinstance(operator_fill_status, dict):
        operator_fill_status = {}
        out["operator_fill_status"] = operator_fill_status
        reasons.append("created operator_fill_status object")

    if placeholders_present:
        operator_fill_status["placeholder_free"] = False
        reasons.append("left operator_fill_status.placeholder_free=false because placeholders remain")
        operator_fill_status["ready_for_import"] = False
        reasons.append("left operator_fill_status.ready_for_import=false because blockers remain")
    else:
        if operator_fill_status.get("placeholder_free") is not True:
            operator_fill_status["placeholder_free"] = True
            reasons.append("set operator_fill_status.placeholder_free=true")

    source_families = out.get("source_families")
    query_terms = out.get("query_terms")
    has_real_sources = (
        isinstance(source_families, list)
        and bool(source_families)
        and all(str(x).strip() for x in source_families)
        and isinstance(query_terms, list)
        and bool(query_terms)
        and all(str(x).strip() for x in query_terms)
    )
    if has_real_sources:
        if operator_fill_status.get("real_sources_attached") is not True:
            operator_fill_status["real_sources_attached"] = True
            reasons.append("set operator_fill_status.real_sources_attached=true")
    else:
        operator_fill_status["real_sources_attached"] = False
        reasons.append("left operator_fill_status.real_sources_attached=false because real source metadata is incomplete")

    norm_domains = _normalize_tokens(out.get("domains", [])) if isinstance(out.get("domains"), list) else []
    norm_jurisdictions = _normalize_tokens(out.get("jurisdictions", [])) if isinstance(out.get("jurisdictions"), list) else []

    semantics_ok = True
    for field in ("entity_name", "audit_type", "industry"):
        if not isinstance(out.get(field), str) or not out.get(field, "").strip():
            reasons.append(f"{field} still missing after safe autofix")
            blocked = True
            semantics_ok = False
    if not has_real_sources:
        reasons.append("source_families/query_terms still incomplete after safe autofix")
        blocked = True
        semantics_ok = False
    if not isinstance(out.get("top_k"), int) or out.get("top_k", 0) <= 0:
        reasons.append("top_k still missing or invalid after safe autofix")
        blocked = True
        semantics_ok = False
    if norm_domains != expected_domains:
        reasons.append(f"domains still mismatch expected={expected_domains} actual={norm_domains}")
        blocked = True
        semantics_ok = False
    if norm_jurisdictions != expected_jurisdictions:
        reasons.append(f"jurisdictions still mismatch expected={expected_jurisdictions} actual={norm_jurisdictions}")
        blocked = True
        semantics_ok = False

    if semantics_ok and not placeholders_present and has_real_sources:
        if operator_fill_status.get("ready_for_import") is not True:
            operator_fill_status["ready_for_import"] = True
            reasons.append("set operator_fill_status.ready_for_import=true")
    else:
        operator_fill_status["ready_for_import"] = False
        reasons.append("left operator_fill_status.ready_for_import=false because semantic blockers remain")

    return out, reasons, blocked


def patch_expected_assertions(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str], bool]:
    out = dict(payload)
    reasons: list[str] = []
    blocked = False

    rules = out.get("rules")
    if not isinstance(rules, dict):
        rules = {}
        out["rules"] = rules
        reasons.append("created rules object")

    for key, value in SAFE_EXPECTED_ASSERTION_RULES.items():
        if rules.get(key) is not True:
            rules[key] = value
            reasons.append(f"set rules.{key}=true")

    expected = out.get("expected")
    if isinstance(expected, dict):
        changed_expected = False
        for key in ("equals", "contains", "minimums"):
            if key not in expected or expected.get(key) is None:
                expected[key] = {}
                changed_expected = True
            elif not isinstance(expected.get(key), dict):
                reasons.append(f"expected.{key} invalid type; left unresolved")
                blocked = True
        if changed_expected:
            reasons.append("normalized expected.equals/contains/minimums objects")
        if (
            isinstance(expected.get("equals"), dict)
            and isinstance(expected.get("contains"), dict)
            and isinstance(expected.get("minimums"), dict)
            and not any([expected["equals"], expected["contains"], expected["minimums"]])
        ):
            reasons.append("expected has no meaningful values; left unresolved")
            blocked = True
        return out, reasons, blocked

    assertions = out.get("expected_assertions")
    if not isinstance(assertions, list) or not assertions:
        reasons.append("expected_assertions missing or empty; left unresolved")
        blocked = True
        return out, reasons, blocked

    normalized_count = 0
    meaningful_values = 0
    for idx, row in enumerate(assertions):
        if not isinstance(row, dict):
            reasons.append(f"expected_assertions[{idx}] not object; left unresolved")
            blocked = True
            continue
        if not isinstance(row.get("assertion_id"), str) or not row.get("assertion_id", "").strip():
            row["assertion_id"] = f"assertion_{idx + 1:03d}"
            normalized_count += 1
        row_type = row.get("type")
        if not isinstance(row_type, str) or not row_type.strip():
            row["type"] = "finding"
            normalized_count += 1
        elif row_type not in ALLOWED_ASSERTION_TYPES:
            reasons.append(f"expected_assertions[{idx}].type invalid and left unchanged: {row_type}")
            blocked = True
        if "control_id" not in row:
            row["control_id"] = ""
            normalized_count += 1
        if "regime_id" not in row:
            row["regime_id"] = ""
            normalized_count += 1

        expected_value = row.get("expected_value")
        if isinstance(expected_value, str) and expected_value.strip():
            meaningful_values += 1
        else:
            reasons.append(f"expected_assertions[{idx}].expected_value still missing")
            blocked = True

        evidence_refs = row.get("evidence_refs")
        if evidence_refs is None:
            reasons.append(f"expected_assertions[{idx}].evidence_refs missing; left unresolved")
            blocked = True
        elif not isinstance(evidence_refs, list):
            reasons.append(f"expected_assertions[{idx}].evidence_refs invalid type; left unresolved")
            blocked = True
        elif not evidence_refs or not all(str(x).strip() for x in evidence_refs):
            reasons.append(f"expected_assertions[{idx}].evidence_refs empty or invalid; left unresolved")
            blocked = True

    if normalized_count > 0:
        reasons.append(f"normalized {normalized_count} assertion schema fields")
    if meaningful_values == 0:
        reasons.append("no meaningful expected_value entries present")
        blocked = True
    return out, reasons, blocked


def trim_case_notes(path: Path) -> tuple[str, bool, bool]:
    if not path.exists():
        return "case_notes missing", False, True
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "case_notes unreadable", False, True
    trimmed = text.strip()
    if not trimmed:
        return "case_notes empty", False, True
    if trimmed != text:
        atomic_write_text(path, trimmed + "\n")
        return "trimmed case_notes whitespace", True, False
    return "case_notes unchanged", False, False


def sync_workspace_entry(entry: dict[str, Any], source_dir: Path, placeholders_present: bool) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    changed = False
    repair = entry.get("operator_repair")
    if not isinstance(repair, dict):
        repair = {}
        entry["operator_repair"] = repair
        changed = True
        reasons.append("created operator_repair object")

    files_present = repair.get("files_present")
    if not isinstance(files_present, dict):
        files_present = {}
        repair["files_present"] = files_present
        changed = True
        reasons.append("created operator_repair.files_present object")

    for rel in entry.get("required_files", []):
        actual = (source_dir / rel).exists()
        if files_present.get(rel) != actual:
            files_present[rel] = actual
            changed = True
            reasons.append(f"synchronized files_present[{rel}]={actual}")

    if not placeholders_present and repair.get("placeholders_removed") is not True:
        repair["placeholders_removed"] = True
        changed = True
        reasons.append("set placeholders_removed=true because no placeholders were found")

    return changed, reasons


def process_item(entry: dict[str, Any], backup_root: Path, write: bool) -> ItemResult:
    item_id = str(entry.get("id", "")).strip()
    kind = str(entry.get("kind", "")).strip()
    source_dir_rel = str(entry.get("source_dir", "")).strip()
    source_dir = ROOT / safe_rel_path(source_dir_rel)
    expected_domains = [normalize_slug(str(x)) for x in entry.get("domains", [])]
    expected_jurisdictions = [normalize_slug(str(x)) for x in entry.get("jurisdictions", [])]

    reasons: list[str] = []
    mutations: list[FileMutation] = []
    blocked = False
    changed = False
    backup_dir: Path | None = None

    if not source_dir.exists():
        return ItemResult(
            item_id=item_id,
            kind=kind,
            source_dir=source_dir_rel,
            changed=False,
            blocked=True,
            backup_dir=None,
            mutations=[],
            reasons=[f"source_dir missing: {source_dir_rel}"],
        )

    placeholders = scan_placeholders(source_dir)
    placeholders_present = bool(placeholders)
    if placeholders_present:
        reasons.append(f"placeholders still present: {len(placeholders)}")
        blocked = True

    audit_context_path = source_dir / "audit_context.json"
    audit_context = read_json_object(audit_context_path)
    if audit_context is None:
        reasons.append("audit_context.json missing or invalid; safe autofix cannot repair invalid json")
        blocked = True
    else:
        patched_audit_context, audit_reasons, audit_blocked = patch_audit_context(
            payload=audit_context,
            expected_domains=expected_domains,
            expected_jurisdictions=expected_jurisdictions,
            placeholders_present=placeholders_present,
        )
        reasons.extend(audit_reasons)
        blocked = blocked or audit_blocked
        audit_changed = json_changed(audit_context, patched_audit_context)
        mutations.append(
            FileMutation(
                path=str(audit_context_path.relative_to(ROOT)),
                changed=audit_changed,
                reason="; ".join(audit_reasons) if audit_reasons else "no change",
            )
        )
        if audit_changed:
            if write and backup_dir is None:
                backup_dir = ensure_backup(source_dir, backup_root)
            if write:
                atomic_write_json(audit_context_path, patched_audit_context)
            changed = True

    if kind == "gold_case":
        expected_assertions_path = source_dir / "expected_assertions.json"
        expected_assertions = read_json_object(expected_assertions_path)
        if expected_assertions is None:
            reasons.append("expected_assertions.json missing or invalid; safe autofix cannot repair invalid json")
            blocked = True
        else:
            patched_expected_assertions, assertion_reasons, assertion_blocked = patch_expected_assertions(expected_assertions)
            reasons.extend(assertion_reasons)
            blocked = blocked or assertion_blocked
            expected_changed = json_changed(expected_assertions, patched_expected_assertions)
            mutations.append(
                FileMutation(
                    path=str(expected_assertions_path.relative_to(ROOT)),
                    changed=expected_changed,
                    reason="; ".join(assertion_reasons) if assertion_reasons else "no change",
                )
            )
            if expected_changed:
                if write and backup_dir is None:
                    backup_dir = ensure_backup(source_dir, backup_root)
                if write:
                    atomic_write_json(expected_assertions_path, patched_expected_assertions)
                changed = True

        case_notes_path = source_dir / "case_notes.md"
        case_notes_reason, case_notes_changed, case_notes_blocked = trim_case_notes(case_notes_path)
        mutations.append(
            FileMutation(
                path=str(case_notes_path.relative_to(ROOT)),
                changed=case_notes_changed,
                reason=case_notes_reason,
            )
        )
        reasons.append(case_notes_reason)
        blocked = blocked or case_notes_blocked
        if case_notes_changed:
            if write and backup_dir is None:
                backup_dir = ensure_backup(source_dir, backup_root)
            changed = True

    workspace_changed, workspace_reasons = sync_workspace_entry(entry, source_dir, placeholders_present)
    reasons.extend(workspace_reasons)
    mutations.append(
        FileMutation(
            path="repair_workspace.json::operator_repair",
            changed=workspace_changed,
            reason="; ".join(workspace_reasons) if workspace_reasons else "no change",
        )
    )

    return ItemResult(
        item_id=item_id,
        kind=kind,
        source_dir=source_dir_rel,
        changed=changed or workspace_changed,
        blocked=blocked,
        backup_dir=str(backup_dir.relative_to(ROOT)) if backup_dir else None,
        mutations=mutations,
        reasons=reasons,
    )


def render_md(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Proof Intake Safe Autofix Report")
    lines.append("")
    lines.append(f"- generated_at_epoch: `{report['generated_at_epoch']}`")
    lines.append(f"- mode: `{report['mode']}`")
    lines.append(f"- entry_count: `{report['entry_count']}`")
    lines.append(f"- changed_count: `{report['changed_count']}`")
    lines.append(f"- blocked_count: `{report['blocked_count']}`")
    lines.append(f"- workspace_changed: `{report['workspace_changed']}`")
    lines.append("")
    for row in report["items"]:
        lines.append(f"## {row['item_id']}")
        lines.append("")
        lines.append(f"- kind: `{row['kind']}`")
        lines.append(f"- source_dir: `{row['source_dir']}`")
        lines.append(f"- changed: `{row['changed']}`")
        lines.append(f"- blocked: `{row['blocked']}`")
        lines.append(f"- backup_dir: `{row['backup_dir']}`")
        lines.append("- reasons:")
        for reason in row["reasons"]:
            lines.append(f"  - {reason}")
        lines.append("- mutations:")
        for mutation in row["mutations"]:
            lines.append(f"  - `{mutation['path']}` changed=`{mutation['changed']}` reason=`{mutation['reason']}`")
        lines.append("")
    if report.get("verifier_result"):
        verifier = report["verifier_result"]
        lines.append("## Verifier Result")
        lines.append("")
        lines.append(f"- passed: `{verifier['passed']}`")
        lines.append(f"- returncode: `{verifier['returncode']}`")
        lines.append(f"- duration_seconds: `{verifier['duration_seconds']}`")
        lines.append("")
    return "\n".join(lines) + "\n"


def run_verifier(workspace_json: Path) -> dict[str, Any]:
    started = time.time()
    proc = subprocess.run(
        [
            os.fspath(Path(os.sys.executable)),
            os.fspath(VERIFIER_SCRIPT),
            "--workspace-json",
            os.fspath(workspace_json),
            "--report-json",
            os.fspath(ROOT / "logs" / "proof_density" / "repair_acceleration" / "proof_batch_real_002.repair_verification.json"),
            "--report-md",
            os.fspath(ROOT / "logs" / "proof_density" / "repair_acceleration" / "proof_batch_real_002.repair_verification.md"),
            "--verified-manifest",
            os.fspath(ROOT / "config" / "proof_batch_real_002.verified_ready_only.json"),
        ],
        cwd=os.fspath(ROOT),
        env={**os.environ, "PYTHONPATH": "."},
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "passed": proc.returncode == 0,
        "returncode": proc.returncode,
        "duration_seconds": round(time.time() - started, 3),
        "stdout_tail": proc.stdout[-12000:],
        "stderr_tail": proc.stderr[-12000:],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply only safe deterministic autofixes to blocked proof intake items")
    parser.add_argument("--workspace-json", default=str(DEFAULT_WORKSPACE_JSON))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    parser.add_argument("--backup-root", default=str(DEFAULT_BACKUP_ROOT))
    parser.add_argument("--workspace-backup", default=str(DEFAULT_WORKSPACE_BACKUP))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--run-verifier", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace_path = Path(args.workspace_json)
    workspace = load_json(workspace_path)
    entries = workspace.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("workspace must contain non-empty entries")

    original_workspace_text = workspace_path.read_text(encoding="utf-8")

    backup_root = resolve_path(args.backup_root)
    workspace_backup = resolve_path(args.workspace_backup)
    results = [process_item(entry=entry, backup_root=backup_root, write=bool(args.write)) for entry in entries]

    workspace_changed = original_workspace_text != (json.dumps(workspace, indent=2, sort_keys=False) + "\n")
    if args.write and workspace_changed:
        atomic_write_text(workspace_backup, original_workspace_text)
        atomic_write_json(workspace_path, workspace)

    report = {
        "generated_at_epoch": int(time.time()),
        "mode": "write" if args.write else "dry_run",
        "entry_count": len(results),
        "changed_count": sum(1 for row in results if row.changed),
        "blocked_count": sum(1 for row in results if row.blocked),
        "workspace_changed": workspace_changed,
        "workspace_backup": str(workspace_backup) if args.write and workspace_changed else None,
        "items": [
            {
                "item_id": row.item_id,
                "kind": row.kind,
                "source_dir": row.source_dir,
                "changed": row.changed,
                "blocked": row.blocked,
                "backup_dir": row.backup_dir,
                "mutations": [{"path": mutation.path, "changed": mutation.changed, "reason": mutation.reason} for mutation in row.mutations],
                "reasons": row.reasons,
            }
            for row in results
        ],
        "verifier_result": None,
    }

    if args.run_verifier:
        report["verifier_result"] = run_verifier(workspace_path)

    atomic_write_json(Path(args.report_json), report)
    atomic_write_text(Path(args.report_md), render_md(report))

    print(
        json.dumps(
            {
                "mode": report["mode"],
                "entry_count": report["entry_count"],
                "changed_count": report["changed_count"],
                "blocked_count": report["blocked_count"],
                "workspace_changed": report["workspace_changed"],
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "verifier_result": report["verifier_result"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
