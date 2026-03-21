from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
DEFAULT_CONFIG = ROOT / "config" / "tenet_build_bible_rules.json"
DEFAULT_OUTPUT_JSON = ROOT / "logs" / "bible_alignment" / "alignment_report.json"
DEFAULT_OUTPUT_MD = ROOT / "logs" / "bible_alignment" / "alignment_report.md"

TEXT_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".json", ".yaml", ".yml",
    ".css", ".scss", ".html", ".txt", ".sql",
}
FRONTEND_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".css", ".scss", ".html", ".md"}


@dataclass(frozen=True)
class Issue:
    severity: str
    category: str
    path: str
    message: str
    line: int | None = None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def normalize(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def existing_paths(candidates: list[str]) -> list[Path]:
    out: list[Path] = []
    for rel in candidates:
        p = ROOT / rel
        if p.exists():
            out.append(p)
    return out


def normalized_allowlist(config: dict[str, Any], key: str) -> set[str]:
    values = config.get(key, [])
    if not isinstance(values, list):
        return set()
    out: set[str] = set()
    for item in values:
        if not isinstance(item, str) or not item.strip():
            continue
        out.add(item.strip().replace("\\", "/"))
    return out


def iter_text_files(root: Path, *, extensions: set[str] | None = None) -> list[Path]:
    allowed = extensions or TEXT_EXTENSIONS
    files: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in allowed:
            files.append(p)
    return sorted(files)


def scan_for_markers(
    *,
    roots: list[Path],
    markers: list[str],
    category: str,
    severity: str,
    max_hits_per_file: int,
    extensions: set[str] | None = None,
) -> list[Issue]:
    issues: list[Issue] = []
    for root in roots:
        for file_path in iter_text_files(root, extensions=extensions):
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            hits = 0
            for idx, line in enumerate(text.splitlines(), start=1):
                for marker in markers:
                    if marker in line:
                        issues.append(
                            Issue(
                                severity=severity,
                                category=category,
                                path=normalize(file_path),
                                message=f"forbidden marker `{marker}`",
                                line=idx,
                            )
                        )
                        hits += 1
                        if hits >= max_hits_per_file:
                            break
                if hits >= max_hits_per_file:
                    break
    return issues


def check_required_paths(config: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    required_any = config.get("required_paths_any", [])
    if required_any and not any((ROOT / rel).exists() for rel in required_any):
        issues.append(
            Issue(
                severity="error",
                category="repo_structure",
                path=".",
                message=f"none of required_paths_any exist: {required_any}",
            )
        )
    for rel in config.get("required_paths_all", []):
        if not (ROOT / rel).exists():
            issues.append(
                Issue(
                    severity="error",
                    category="repo_structure",
                    path=".",
                    message=f"missing required path: {rel}",
                )
            )
    return issues


def _gold_case_dirs(config: dict[str, Any]) -> list[Path]:
    case_dirs: list[Path] = []
    for root in existing_paths(config.get("gold_case_roots", [])):
        if not root.is_dir():
            continue
        for child in sorted(p for p in root.iterdir() if p.is_dir()):
            if (child / "audit_context.json").exists() or (child / "expected_assertions.json").exists():
                case_dirs.append(child)
    return case_dirs


def validate_gold_case_dir(*, case_dir: Path, config: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    audit_path = case_dir / "audit_context.json"
    expected_path = case_dir / "expected_assertions.json"

    try:
        audit_payload = load_json(audit_path)
    except Exception as exc:
        return [Issue("error", "gold_case_contract", normalize(audit_path), f"invalid json: {exc}")]

    if not isinstance(audit_payload, dict):
        issues.append(Issue("error", "gold_case_contract", normalize(audit_path), "json must be an object"))
    else:
        for key in config["required_bools_in_audit_context"]:
            if audit_payload.get(key) is not True:
                issues.append(Issue("error", "gold_case_contract", normalize(audit_path), f"{key} must be true"))
        if not isinstance(audit_payload.get("domains"), list) or not audit_payload.get("domains"):
            issues.append(Issue("error", "gold_case_contract", normalize(audit_path), "domains must be a non-empty list"))
        if not isinstance(audit_payload.get("jurisdictions"), list) or not audit_payload.get("jurisdictions"):
            issues.append(Issue("error", "gold_case_contract", normalize(audit_path), "jurisdictions must be a non-empty list"))

    try:
        expected_payload = load_json(expected_path)
    except Exception as exc:
        issues.append(Issue("error", "gold_case_contract", normalize(expected_path), f"invalid json: {exc}"))
        return issues

    if not isinstance(expected_payload, dict):
        issues.append(Issue("error", "gold_case_contract", normalize(expected_path), "json must be an object"))
        return issues

    rules = expected_payload.get("rules")
    if not isinstance(rules, dict):
        issues.append(Issue("error", "gold_case_contract", normalize(expected_path), "rules must be an object"))
    else:
        for key in config["required_bools_in_expected_assertions_rules"]:
            if rules.get(key) is not True:
                issues.append(Issue("error", "gold_case_contract", normalize(expected_path), f"rules.{key} must be true"))

    expected = expected_payload.get("expected")
    if not isinstance(expected, dict):
        issues.append(Issue("error", "gold_case_contract", normalize(expected_path), "expected must be an object"))
        return issues

    equals = expected.get("equals")
    contains = expected.get("contains")
    minimums = expected.get("minimums")
    if not isinstance(equals, dict):
        issues.append(Issue("error", "gold_case_contract", normalize(expected_path), "expected.equals must be an object"))
    if not isinstance(contains, dict):
        issues.append(Issue("error", "gold_case_contract", normalize(expected_path), "expected.contains must be an object"))
    if not isinstance(minimums, dict):
        issues.append(Issue("error", "gold_case_contract", normalize(expected_path), "expected.minimums must be an object"))

    if isinstance(equals, dict) and isinstance(contains, dict) and isinstance(minimums, dict):
        if not any([equals, contains, minimums]):
            issues.append(Issue("error", "gold_case_contract", normalize(expected_path), "expected must contain at least one meaningful assertion"))

    return issues


def check_gold_case_contracts(config: dict[str, Any]) -> list[Issue]:
    case_dirs = _gold_case_dirs(config)
    if not case_dirs:
        return [Issue("warning", "gold_case_contract", ".", "no gold case roots found")]
    issues: list[Issue] = []
    for case_dir in case_dirs:
        issues.extend(validate_gold_case_dir(case_dir=case_dir, config=config))
    return issues


def check_deterministic_purity(config: dict[str, Any]) -> list[Issue]:
    roots = existing_paths(config.get("deterministic_roots", []))
    if not roots:
        return [Issue("warning", "deterministic_purity", ".", "no deterministic roots found")]
    issues: list[Issue] = []
    forbidden = config.get("forbidden_in_deterministic_code", [])
    allowlist = normalized_allowlist(config, "model_boundary_allowlist")
    for root in roots:
        for file_path in iter_text_files(root, extensions={".py"}):
            if normalize(file_path) in allowlist:
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for idx, line in enumerate(text.splitlines(), start=1):
                for marker in forbidden:
                    if marker in line:
                        issues.append(
                            Issue(
                                severity="error",
                                category="deterministic_purity",
                                path=normalize(file_path),
                                message=f"forbidden deterministic dependency `{marker}`",
                                line=idx,
                            )
                        )
    return issues


def check_ui_style(config: dict[str, Any]) -> list[Issue]:
    roots = existing_paths(config.get("frontend_roots", []))
    if not roots:
        return [Issue("warning", "ui_style", ".", "no frontend roots found")]
    issues: list[Issue] = []
    issues.extend(
        scan_for_markers(
            roots=roots,
            markers=config["forbidden_text_markers"],
            category="ui_style",
            severity="error",
            max_hits_per_file=int(config["max_forbidden_hits_per_file"]),
            extensions=FRONTEND_EXTENSIONS,
        )
    )
    issues.extend(
        scan_for_markers(
            roots=roots,
            markers=config["forbidden_ui_markers"],
            category="ui_style",
            severity="warning",
            max_hits_per_file=int(config["max_forbidden_hits_per_file"]),
            extensions=FRONTEND_EXTENSIONS,
        )
    )
    return issues


def check_report_surface(config: dict[str, Any]) -> list[Issue]:
    roots = existing_paths(config.get("report_roots", []))
    if not roots:
        return [Issue("warning", "report_surface", ".", "no report roots found")]

    found_report_surface = False
    found_export_surface = False
    for root in roots:
        for file_path in iter_text_files(root):
            text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
            if "board_memo_markdown" in text or "client_report_markdown" in text or "regulator_memo_markdown" in text:
                found_report_surface = True
            if "pdf" in text or "docx" in text:
                found_export_surface = True

    issues: list[Issue] = []
    if not found_report_surface:
        issues.append(Issue("warning", "report_surface", ".", "no deterministic report surface detected"))
    if not found_export_surface:
        issues.append(Issue("warning", "report_surface", ".", "no docx/pdf export surface detected"))
    return issues


def build_summary(issues: list[Issue]) -> dict[str, Any]:
    severity_counts = Counter(issue.severity for issue in issues)
    category_counts = Counter(issue.category for issue in issues)
    status = "green"
    if severity_counts.get("error", 0) > 0:
        status = "red"
    elif severity_counts.get("warning", 0) > 0:
        status = "amber"
    return {
        "status": status,
        "severity_counts": dict(sorted(severity_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "issue_count": len(issues),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Tenet Build Bible Alignment Report",
        "",
        f"- governing_bible_version: `{report.get('governing_bible_version', 'unknown')}`",
        f"- governing_bible_path: `{report.get('governing_bible_path', 'unknown')}`",
        f"- generated_at_epoch: `{report['generated_at_epoch']}`",
        f"- status: `{report['summary']['status']}`",
        f"- issue_count: `{report['summary']['issue_count']}`",
        "",
        "## Severity Counts",
        "",
    ]
    for key, value in report["summary"]["severity_counts"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Category Counts", ""])
    for key, value in report["summary"]["category_counts"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Issues", ""])
    for issue in report["issues"]:
        suffix = f":{issue['line']}" if issue["line"] is not None else ""
        lines.append(f"- [{issue['severity']}] `{issue['category']}` `{issue['path']}{suffix}` - {issue['message']}")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tenet build bible alignment gate")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_json(Path(args.config))
    issues: list[Issue] = []
    issues.extend(check_required_paths(config))
    issues.extend(check_deterministic_purity(config))
    issues.extend(check_gold_case_contracts(config))
    issues.extend(check_ui_style(config))
    issues.extend(check_report_surface(config))

    report = {
        "version": str(config.get("version", "v1")),
        "governing_bible_version": str(config.get("governing_bible_version", "unknown")),
        "governing_bible_path": str(config.get("governing_bible_path", "unknown")),
        "generated_at_epoch": int(time.time()),
        "summary": build_summary(issues),
        "issues": [
            {
                "severity": issue.severity,
                "category": issue.category,
                "path": issue.path,
                "message": issue.message,
                "line": issue.line,
            }
            for issue in issues
        ],
    }
    atomic_write(Path(args.output_json), json.dumps(report, indent=2) + "\n")
    atomic_write(Path(args.output_md), render_markdown(report))

    print(json.dumps({
        "version": report["version"],
        "governing_bible_version": report["governing_bible_version"],
        "status": report["summary"]["status"],
        "issue_count": report["summary"]["issue_count"],
        "severity_counts": report["summary"]["severity_counts"],
        "category_counts": report["summary"]["category_counts"],
        "output_json": str(Path(args.output_json)),
        "output_md": str(Path(args.output_md)),
    }, indent=2))

    if args.strict and report["summary"]["severity_counts"].get("error", 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
