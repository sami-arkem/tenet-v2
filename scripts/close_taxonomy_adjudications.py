from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


ROOT = Path.cwd()

DEFAULT_DOSSIER_INDEX = ROOT / "logs" / "bible_alignment" / "taxonomy_adjudication" / "dossier_index.json"
DEFAULT_DECISIONS_JSON = ROOT / "config" / "gold_case_taxonomy_adjudications.json"
DEFAULT_OUTPUT_JSON = ROOT / "logs" / "bible_alignment" / "taxonomy_adjudication" / "closure_report.json"
DEFAULT_OUTPUT_MD = ROOT / "logs" / "bible_alignment" / "taxonomy_adjudication" / "closure_report.md"
DEFAULT_OUTPUT_DIR = ROOT / "logs" / "bible_alignment" / "taxonomy_adjudication"
DEFAULT_BACKUP_ROOT = ROOT / "logs" / "bible_alignment" / "taxonomy_adjudication_closure_backups"

APPLY_SCRIPT = ROOT / "scripts" / "gold_case_taxonomy_adjudication.py"
BIBLE_GATE_SCRIPT = ROOT / "scripts" / "bible_alignment_gate.py"
PROGRAM_CONTROL_SCRIPT = ROOT / "scripts" / "tenet_program_control.py"

ALLOWED_DOMAINS = {
    "aml",
    "kyc",
    "kyb",
    "sanctions",
    "governance",
    "vendor_risk",
    "third_party_risk",
    "fraud",
    "transaction_screening",
    "regulatory_reporting",
    "regulatory_licensing",
    "remediation_tracking",
}

ALLOWED_JURISDICTIONS = {
    "global",
    "eu",
    "uk",
    "us",
    "uae",
    "singapore",
    "india",
    "hong_kong",
    "canada",
    "australia",
}


@dataclass(frozen=True)
class ClosureIssue:
    severity: str
    code: str
    case_dir: str
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


def normalize_rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def safe_rel_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"absolute path not allowed: {value}")
    if ".." in path.parts:
        raise ValueError(f"parent traversal not allowed: {value}")
    return path


def read_dossier_index(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"missing dossier index: {path}")
    payload = load_json(path)
    dossiers = payload.get("dossiers")
    if not isinstance(dossiers, list):
        raise ValueError("dossier_index.json missing dossiers list")
    out: list[str] = []
    for row in dossiers:
        if not isinstance(row, dict):
            raise ValueError("dossier entry must be object")
        case_dir = str(row.get("case_dir", "")).strip()
        if not case_dir:
            raise ValueError("dossier entry missing case_dir")
        out.append(case_dir)
    return sorted(set(out))


def _norm_list(values: Any, allowed: set[str], label: str, case_dir: str) -> list[str]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{case_dir}: {label} must be non-empty list")
    out: list[str] = []
    for value in values:
        token = str(value).strip().lower()
        if token not in allowed:
            raise ValueError(f"{case_dir}: invalid {label[:-1]} `{token}`")
        out.append(token)
    return sorted(set(out))


def read_decisions(path: Path) -> tuple[list[dict[str, Any]], list[ClosureIssue]]:
    if not path.exists():
        return [], [ClosureIssue("error", "decision.file_missing", ".", f"missing decisions file: {path}")]
    payload = load_json(path)
    rows = payload.get("decisions")
    if not isinstance(rows, list):
        return [], [ClosureIssue("error", "decision.list_missing", ".", "decisions json missing decisions list")]
    return rows, []


def validate_decisions_against_dossiers(
    *,
    dossier_case_dirs: list[str],
    decision_rows: list[dict[str, Any]],
) -> tuple[list[ClosureIssue], list[dict[str, Any]], list[str]]:
    issues: list[ClosureIssue] = []
    normalized_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    dossier_set = set(dossier_case_dirs)

    for row in decision_rows:
        if not isinstance(row, dict):
            issues.append(ClosureIssue("error", "decision.not_object", ".", "decision row must be object"))
            continue
        case_dir = str(row.get("case_dir", "")).strip()
        if not case_dir:
            issues.append(ClosureIssue("error", "decision.missing_case_dir", ".", "decision row missing case_dir"))
            continue
        decided_by = str(row.get("decided_by", "")).strip()
        rationale = str(row.get("rationale", "")).strip()
        evidence_refs = row.get("evidence_refs")
        domains = row.get("domains")
        jurisdictions = row.get("jurisdictions")

        if case_dir in seen:
            issues.append(ClosureIssue("error", "decision.duplicate_case_dir", case_dir, "duplicate decision for case_dir"))
            continue
        seen.add(case_dir)

        if case_dir not in dossier_set:
            issues.append(ClosureIssue("error", "decision.case_not_in_dossier_set", case_dir, "decision provided for non-target case"))
            continue
        if not decided_by:
            issues.append(ClosureIssue("error", "decision.missing_decided_by", case_dir, "decided_by must be non-empty"))
        if not rationale:
            issues.append(ClosureIssue("error", "decision.missing_rationale", case_dir, "rationale must be non-empty"))
        if not isinstance(evidence_refs, list) or not evidence_refs or not all(str(x).strip() for x in evidence_refs):
            issues.append(ClosureIssue("error", "decision.invalid_evidence_refs", case_dir, "evidence_refs must be non-empty list of strings"))

        try:
            norm_domains = _norm_list(domains, ALLOWED_DOMAINS, "domains", case_dir)
            norm_jurisdictions = _norm_list(jurisdictions, ALLOWED_JURISDICTIONS, "jurisdictions", case_dir)
        except ValueError as exc:
            issues.append(ClosureIssue("error", "decision.invalid_taxonomy", case_dir, str(exc)))
            continue

        normalized_rows.append({
            "case_dir": case_dir,
            "domains": norm_domains,
            "jurisdictions": norm_jurisdictions,
            "decided_by": decided_by,
            "rationale": rationale,
            "evidence_refs": [str(x).strip() for x in evidence_refs],
        })

    missing = sorted(dossier_set - seen)
    for case_dir in missing:
        issues.append(ClosureIssue("error", "decision.missing_for_target_case", case_dir, "no decision supplied for target case"))
    return issues, normalized_rows, missing


def build_adjudication_queue(
    *,
    dossier_case_dirs: list[str],
    decisions_rows: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    decision_map = {
        str(row.get("case_dir", "")).strip(): row
        for row in decisions_rows
        if isinstance(row, dict)
    }
    rows = []
    for idx, case_dir in enumerate(dossier_case_dirs, start=1):
        row = decision_map.get(case_dir)
        if row is None:
            status = "missing"
            domains = None
            jurisdictions = None
            decided_by = None
        else:
            status = "present"
            domains = row.get("domains")
            jurisdictions = row.get("jurisdictions")
            decided_by = row.get("decided_by")
        rows.append({
            "priority": idx,
            "case_dir": case_dir,
            "status": status,
            "domains": domains,
            "jurisdictions": jurisdictions,
            "decided_by": decided_by,
        })

    queue = {
        "generated_at_epoch": int(time.time()),
        "target_case_count": len(dossier_case_dirs),
        "rows": rows,
    }
    atomic_write_json(output_dir / "adjudication_queue.json", queue)

    md_lines = ["# Taxonomy Adjudication Queue", ""]
    for row in rows:
        md_lines.append(f"{row['priority']}. `{row['case_dir']}`")
        md_lines.append(f"   - status: `{row['status']}`")
        md_lines.append(f"   - domains: `{row['domains']}`")
        md_lines.append(f"   - jurisdictions: `{row['jurisdictions']}`")
        md_lines.append(f"   - decided_by: `{row['decided_by']}`")
        md_lines.append("")
    atomic_write_text(output_dir / "adjudication_queue.md", "\n".join(md_lines))
    return queue


def run_cmd(argv: list[str], timeout_seconds: int = 2400) -> dict[str, Any]:
    started = time.time()
    proc = subprocess.run(
        argv,
        cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": "."},
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "cmd": argv,
        "returncode": proc.returncode,
        "passed": proc.returncode == 0,
        "duration_seconds": round(time.time() - started, 3),
        "stdout_tail": proc.stdout[-12000:],
        "stderr_tail": proc.stderr[-12000:],
    }


def read_program_control_topline() -> dict[str, Any]:
    report_path = ROOT / "logs" / "program_control" / "program_control_report.json"
    if not report_path.exists():
        return {
            "enterprise_readiness_score": None,
            "blocker_count": None,
            "top_blocker": None,
        }
    payload = load_json(report_path)
    blockers = payload.get("blockers", [])
    return {
        "enterprise_readiness_score": payload.get("score", {}).get("total_score"),
        "blocker_count": len(blockers) if isinstance(blockers, list) else None,
        "top_blocker": blockers[0]["code"] if isinstance(blockers, list) and blockers else None,
    }


def copy_temp_decisions(normalized_rows: list[dict[str, Any]], output_dir: Path) -> Path:
    payload = {"decisions": normalized_rows}
    path = output_dir / "normalized_taxonomy_adjudications.json"
    atomic_write_json(path, payload)
    return path


def apply_decisions_transactionally(
    *,
    normalized_decisions_path: Path,
    backup_root: Path,
    output_dir: Path,
    write: bool,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    apply_result = run_cmd([
        sys.executable,
        str(APPLY_SCRIPT),
        "apply-decisions",
        "--decisions-json",
        str(normalized_decisions_path),
        "--backup-root",
        str(backup_root),
        "--apply-report-json",
        str(output_dir / "apply_report.json"),
        "--apply-report-md",
        str(output_dir / "apply_report.md"),
        *(["--write"] if write else []),
    ])

    bible_gate_result = None
    program_control_result = None
    if apply_result["passed"] and write:
        bible_gate_result = run_cmd([
            sys.executable,
            str(BIBLE_GATE_SCRIPT),
            "--output-json",
            str(ROOT / "logs" / "bible_alignment" / "alignment_report.json"),
            "--output-md",
            str(ROOT / "logs" / "bible_alignment" / "alignment_report.md"),
        ])
        program_control_result = run_cmd([
            sys.executable,
            str(PROGRAM_CONTROL_SCRIPT),
            "--output-json",
            str(ROOT / "logs" / "program_control" / "program_control_report.json"),
            "--output-md",
            str(ROOT / "logs" / "program_control" / "program_control_report.md"),
        ])

    return {
        "apply_result": apply_result,
        "bible_gate_result": bible_gate_result,
        "program_control_result": program_control_result,
        "program_control_topline_after": read_program_control_topline() if write else None,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Taxonomy Adjudication Closure Report",
        "",
        f"- generated_at_epoch: `{report['generated_at_epoch']}`",
        f"- mode: `{report['mode']}`",
        f"- target_case_count: `{report['target_case_count']}`",
        f"- valid_decision_count: `{report['valid_decision_count']}`",
        f"- issue_count: `{report['issue_count']}`",
        "",
        "## Validation Issues",
        "",
    ]
    for issue in report["issues"]:
        lines.append(f"- [{issue['severity']}] `{issue['code']}` `{issue['case_dir']}` - {issue['message']}")
    lines.extend(["", "## Apply Phase", ""])
    for key in ("apply_result", "bible_gate_result", "program_control_result"):
        row = report["execution"].get(key)
        if row is None:
            continue
        lines.append(f"### {key}")
        lines.append(f"- passed: `{row['passed']}`")
        lines.append(f"- returncode: `{row['returncode']}`")
        lines.append(f"- duration_seconds: `{row['duration_seconds']}`")
        lines.append("")
    topline = report["execution"].get("program_control_topline_after")
    if topline:
        lines.append("## Program Control After Apply")
        lines.append("")
        for key, value in topline.items():
            lines.append(f"- {key}: `{value}`")
        lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Close remaining gold-case taxonomy adjudications deterministically")
    parser.add_argument("--dossier-index", default=str(DEFAULT_DOSSIER_INDEX))
    parser.add_argument("--decisions-json", default=str(DEFAULT_DECISIONS_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--backup-root", default=str(DEFAULT_BACKUP_ROOT))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    dossier_case_dirs = read_dossier_index(Path(args.dossier_index))
    decisions_rows, read_issues = read_decisions(Path(args.decisions_json))
    queue = build_adjudication_queue(
        dossier_case_dirs=dossier_case_dirs,
        decisions_rows=decisions_rows,
        output_dir=output_dir,
    )

    validation_issues, normalized_rows, missing = validate_decisions_against_dossiers(
        dossier_case_dirs=dossier_case_dirs,
        decision_rows=decisions_rows,
    )
    issues = [*read_issues, *validation_issues]
    normalized_path = copy_temp_decisions(normalized_rows, output_dir)

    execution = {
        "apply_result": None,
        "bible_gate_result": None,
        "program_control_result": None,
        "program_control_topline_after": None,
    }
    if not issues:
        execution = apply_decisions_transactionally(
            normalized_decisions_path=normalized_path,
            backup_root=Path(args.backup_root),
            output_dir=output_dir,
            write=bool(args.write),
        )

    report = {
        "generated_at_epoch": int(time.time()),
        "mode": "write" if args.write else "dry_run",
        "target_case_count": len(dossier_case_dirs),
        "valid_decision_count": len(normalized_rows),
        "missing_decision_count": len(missing),
        "issue_count": len(issues),
        "issues": [
            {
                "severity": issue.severity,
                "code": issue.code,
                "case_dir": issue.case_dir,
                "message": issue.message,
            }
            for issue in issues
        ],
        "execution": execution,
        "queue": queue,
        "normalized_decisions_path": str(normalized_path),
    }

    atomic_write_json(Path(args.output_json), report)
    atomic_write_text(Path(args.output_md), render_markdown(report))

    print(json.dumps({
        "mode": report["mode"],
        "target_case_count": report["target_case_count"],
        "valid_decision_count": report["valid_decision_count"],
        "missing_decision_count": report["missing_decision_count"],
        "issue_count": report["issue_count"],
        "output_json": str(Path(args.output_json)),
        "output_md": str(Path(args.output_md)),
    }, indent=2))

    if args.strict and report["issue_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
