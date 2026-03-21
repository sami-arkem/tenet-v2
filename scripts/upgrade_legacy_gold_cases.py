from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


ROOT = Path.cwd()
DEFAULT_RULES_PATH = ROOT / "config" / "tenet_build_bible_rules.json"
DEFAULT_REPORT_JSON = ROOT / "logs" / "bible_alignment" / "legacy_gold_upgrade_report.json"
DEFAULT_REPORT_MD = ROOT / "logs" / "bible_alignment" / "legacy_gold_upgrade_report.md"

DEFAULT_REQUIRED_AUDIT_FLAGS = {
    "historical_context_is_non_authoritative": True,
    "deterministic_current_audit_truth_only": True,
}

DEFAULT_REQUIRED_ASSERTION_RULES = {
    "no_invented_pass_outcome": True,
    "deterministic_current_truth_only": True,
    "historical_context_cannot_override_current_truth": True,
}


@dataclass(frozen=True)
class FileChange:
    path: str
    changed: bool
    reason: str


@dataclass(frozen=True)
class CaseUpgradeResult:
    case_dir: str
    changed: bool
    blocked: bool
    reasons: list[str]
    changed_files: list[FileChange]
    backup_dir: str | None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def discover_gold_case_roots(rules: dict[str, Any]) -> list[Path]:
    roots: list[Path] = []
    for rel in rules.get("gold_case_roots", []):
        path = ROOT / rel
        if path.exists():
            roots.append(path)
    return roots


def discover_case_dirs(gold_case_roots: list[Path]) -> list[Path]:
    case_dirs: list[Path] = []
    seen: set[str] = set()
    for root in gold_case_roots:
        if not root.is_dir():
            continue
        for candidate in sorted(p for p in root.iterdir() if p.is_dir()):
            audit_context = candidate / "audit_context.json"
            expected_assertions = candidate / "expected_assertions.json"
            if audit_context.exists() and expected_assertions.exists():
                key = str(candidate.resolve())
                if key not in seen:
                    seen.add(key)
                    case_dirs.append(candidate)
    return case_dirs


def ensure_backup(case_dir: Path, backup_root: Path) -> Path:
    backup_root.mkdir(parents=True, exist_ok=True)
    dest = backup_root / case_dir.name
    suffix = 1
    while dest.exists():
        dest = backup_root / f"{case_dir.name}_{suffix:03d}"
        suffix += 1
    shutil.copytree(case_dir, dest)
    return dest


def patch_audit_context(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str], bool]:
    reasons: list[str] = []
    blocked = False
    if not isinstance(payload, dict):
        return payload, ["audit_context.json is not an object"], True

    for key, value in DEFAULT_REQUIRED_AUDIT_FLAGS.items():
        if payload.get(key) is not True:
            payload[key] = value
            reasons.append(f"set {key}=true")

    domains = payload.get("domains")
    jurisdictions = payload.get("jurisdictions")
    if not isinstance(domains, list) or not domains:
        reasons.append("missing non-empty domains list; left unchanged")
        blocked = True
    if not isinstance(jurisdictions, list) or not jurisdictions:
        reasons.append("missing non-empty jurisdictions list; left unchanged")
        blocked = True

    return payload, reasons, blocked


def patch_expected_file(payload: dict[str, Any], filename: str) -> tuple[dict[str, Any], list[str], bool]:
    reasons: list[str] = []
    blocked = False
    if not isinstance(payload, dict):
        return payload, [f"{filename} is not an object"], True

    expected = payload.get("expected")
    if not isinstance(expected, dict):
        return payload, [f"{filename} missing legacy expected object; left unchanged"], True

    rules = payload.get("rules")
    if not isinstance(rules, dict):
        rules = {}
        payload["rules"] = rules
        reasons.append("created rules object")

    for key, value in DEFAULT_REQUIRED_ASSERTION_RULES.items():
        if rules.get(key) is not True:
            rules[key] = value
            reasons.append(f"set rules.{key}=true")

    equals = expected.get("equals", {})
    contains = expected.get("contains", {})
    minimums = expected.get("minimums", {})
    if not isinstance(equals, dict) or not isinstance(contains, dict) or not isinstance(minimums, dict):
        reasons.append("legacy expected object shape invalid; left unchanged")
        blocked = True
    elif not any([equals, contains, minimums]):
        reasons.append("expected has no meaningful equals/contains/minimums values; left unchanged")
        blocked = True

    return payload, reasons, blocked


def patch_case(case_dir: Path, backup_root: Path, write: bool) -> CaseUpgradeResult:
    reasons: list[str] = []
    changed_files: list[FileChange] = []
    blocked = False
    made_any_change = False
    backup_dir: Path | None = None

    audit_context_path = case_dir / "audit_context.json"
    expected_path = case_dir / "expected_assertions.json"
    if not audit_context_path.exists() or not expected_path.exists():
        return CaseUpgradeResult(
            case_dir=normalize(case_dir),
            changed=False,
            blocked=True,
            reasons=["missing audit_context.json or expected_assertions.json"],
            changed_files=[],
            backup_dir=None,
        )

    audit_original = audit_context_path.read_text(encoding="utf-8")
    expected_original = expected_path.read_text(encoding="utf-8")

    try:
        audit_payload = json.loads(audit_original)
    except Exception as exc:
        return CaseUpgradeResult(
            case_dir=normalize(case_dir),
            changed=False,
            blocked=True,
            reasons=[f"invalid audit_context.json: {exc}"],
            changed_files=[],
            backup_dir=None,
        )

    try:
        expected_payload = json.loads(expected_original)
    except Exception as exc:
        return CaseUpgradeResult(
            case_dir=normalize(case_dir),
            changed=False,
            blocked=True,
            reasons=[f"invalid expected_assertions.json: {exc}"],
            changed_files=[],
            backup_dir=None,
        )

    audit_payload, audit_reasons, audit_blocked = patch_audit_context(audit_payload)
    expected_payload, expected_reasons, expected_blocked = patch_expected_file(expected_payload, expected_path.name)
    reasons.extend(audit_reasons)
    reasons.extend(expected_reasons)
    blocked = audit_blocked or expected_blocked

    audit_new = json.dumps(audit_payload, indent=2, sort_keys=False) + "\n"
    expected_new = json.dumps(expected_payload, indent=2, sort_keys=False) + "\n"

    audit_changed = sha256_text(audit_original) != sha256_text(audit_new)
    expected_changed = sha256_text(expected_original) != sha256_text(expected_new)
    made_any_change = audit_changed or expected_changed

    changed_files.append(
        FileChange(
            path=normalize(audit_context_path),
            changed=audit_changed,
            reason="; ".join(audit_reasons) if audit_reasons else "no change",
        )
    )
    changed_files.append(
        FileChange(
            path=normalize(expected_path),
            changed=expected_changed,
            reason="; ".join(expected_reasons) if expected_reasons else "no change",
        )
    )

    if write and made_any_change:
        backup_dir = ensure_backup(case_dir, backup_root)
        if audit_changed:
            atomic_write_text(audit_context_path, audit_new)
        if expected_changed:
            atomic_write_text(expected_path, expected_new)

    return CaseUpgradeResult(
        case_dir=normalize(case_dir),
        changed=made_any_change,
        blocked=blocked,
        reasons=reasons,
        changed_files=changed_files,
        backup_dir=normalize(backup_dir) if backup_dir else None,
    )


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Legacy Gold Case Upgrade Report",
        "",
        f"- generated_at_epoch: `{report['generated_at_epoch']}`",
        f"- mode: `{report['mode']}`",
        f"- case_count: `{report['summary']['case_count']}`",
        f"- changed_count: `{report['summary']['changed_count']}`",
        f"- blocked_count: `{report['summary']['blocked_count']}`",
        f"- clean_count: `{report['summary']['clean_count']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"]["reason_counts"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Cases", ""])
    for case in report["cases"]:
        lines.append(f"### {case['case_dir']}")
        lines.append(f"- changed: `{case['changed']}`")
        lines.append(f"- blocked: `{case['blocked']}`")
        if case["backup_dir"]:
            lines.append(f"- backup_dir: `{case['backup_dir']}`")
        lines.append("- reasons:")
        for reason in case["reasons"]:
            lines.append(f"  - {reason}")
        lines.append("- changed_files:")
        for row in case["changed_files"]:
            lines.append(f"  - `{row['path']}` changed=`{row['changed']}` reason=`{row['reason']}`")
        lines.append("")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely upgrade legacy gold cases to build-bible contract")
    parser.add_argument("--rules", default=str(DEFAULT_RULES_PATH))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    parser.add_argument("--backup-root", default="logs/bible_alignment/legacy_gold_backups")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rules = load_json(Path(args.rules))
    roots = discover_gold_case_roots(rules)
    if not roots:
        raise SystemExit("No gold case roots found in rules config")

    case_dirs = discover_case_dirs(roots)
    backup_root = ROOT / args.backup_root
    results = [patch_case(case_dir=case_dir, backup_root=backup_root, write=bool(args.write)) for case_dir in case_dirs]

    reason_counts: Counter[str] = Counter()
    blocked_count = 0
    changed_count = 0
    clean_count = 0
    for result in results:
        if result.blocked:
            blocked_count += 1
        if result.changed:
            changed_count += 1
        if (not result.changed) and (not result.blocked):
            clean_count += 1
        for reason in result.reasons:
            reason_counts[reason] += 1

    report = {
        "version": "v1",
        "generated_at_epoch": int(time.time()),
        "mode": "write" if args.write else "dry_run",
        "summary": {
            "case_count": len(results),
            "changed_count": changed_count,
            "blocked_count": blocked_count,
            "clean_count": clean_count,
            "reason_counts": dict(sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))),
        },
        "cases": [
            {
                "case_dir": result.case_dir,
                "changed": result.changed,
                "blocked": result.blocked,
                "reasons": result.reasons,
                "backup_dir": result.backup_dir,
                "changed_files": [
                    {
                        "path": file_change.path,
                        "changed": file_change.changed,
                        "reason": file_change.reason,
                    }
                    for file_change in result.changed_files
                ],
            }
            for result in results
        ],
    }

    atomic_write_json(Path(args.report_json), report)
    atomic_write_text(Path(args.report_md), render_markdown(report))

    print(json.dumps({
        "mode": report["mode"],
        "case_count": report["summary"]["case_count"],
        "changed_count": report["summary"]["changed_count"],
        "blocked_count": report["summary"]["blocked_count"],
        "clean_count": report["summary"]["clean_count"],
        "report_json": str(Path(args.report_json)),
        "report_md": str(Path(args.report_md)),
    }, indent=2))

    if args.strict and blocked_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
