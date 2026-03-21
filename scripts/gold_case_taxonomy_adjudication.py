from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


ROOT = Path.cwd()
DEFAULT_ALIGNMENT_JSON = ROOT / "logs" / "bible_alignment" / "alignment_report.json"
DEFAULT_RECOVERY_JSON = ROOT / "logs" / "bible_alignment" / "taxonomy_recovery_report.json"
DEFAULT_DOSSIER_DIR = ROOT / "logs" / "bible_alignment" / "taxonomy_adjudication"
DEFAULT_DECISIONS_JSON = ROOT / "config" / "gold_case_taxonomy_adjudications.json"
DEFAULT_APPLY_REPORT_JSON = ROOT / "logs" / "bible_alignment" / "taxonomy_adjudication_apply_report.json"
DEFAULT_APPLY_REPORT_MD = ROOT / "logs" / "bible_alignment" / "taxonomy_adjudication_apply_report.md"

TEXT_EXTENSIONS = {".json", ".md", ".txt", ".yaml", ".yml"}

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
class CaseTarget:
    case_dir: Path
    issue_messages: list[str]


@dataclass(frozen=True)
class Decision:
    case_dir: str
    domains: list[str]
    jurisdictions: list[str]
    decided_by: str
    rationale: str
    evidence_refs: list[str]


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
        raise ValueError(f"Absolute path not allowed: {value}")
    if ".." in path.parts:
        raise ValueError(f"Parent traversal not allowed: {value}")
    return path


def extract_targets_from_alignment(alignment_json: Path) -> list[CaseTarget]:
    payload = load_json(alignment_json)
    grouped: dict[str, list[str]] = {}
    for issue in payload.get("issues", []):
        if issue.get("category") != "gold_case_contract":
            continue
        raw_path = str(issue.get("path", "")).strip()
        if not raw_path.endswith("audit_context.json"):
            continue
        message = str(issue.get("message", "")).strip()
        if "domains must be a non-empty list" not in message and "jurisdictions must be a non-empty list" not in message:
            continue
        case_dir = str(Path(raw_path).parent)
        grouped.setdefault(case_dir, []).append(message)
    return [
        CaseTarget(case_dir=ROOT / rel, issue_messages=messages)
        for rel, messages in sorted(grouped.items())
    ]


def read_recovery_context(recovery_json: Path) -> dict[str, Any]:
    if not recovery_json.exists():
        return {}
    payload = load_json(recovery_json)
    context: dict[str, Any] = {}
    for row in payload.get("cases", []):
        case_dir = row.get("case_dir")
        if isinstance(case_dir, str):
            context[case_dir] = row
    return context


def gather_text_snippets(case_dir: Path, max_files: int = 12, max_chars_per_file: int = 1200) -> list[dict[str, str]]:
    snippets: list[dict[str, str]] = []
    files = sorted(p for p in case_dir.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_EXTENSIONS)
    for path in files[:max_files]:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            continue
        if not text:
            continue
        snippets.append({
            "path": normalize_rel(path),
            "snippet": text[:max_chars_per_file],
        })
    return snippets


def infer_folder_hints(case_dir: Path) -> dict[str, list[str]]:
    name = case_dir.name.lower()
    domain_hits: list[str] = []
    jurisdiction_hits: list[str] = []
    for domain in sorted(ALLOWED_DOMAINS):
        if domain in name:
            domain_hits.append(domain)
    for jurisdiction in sorted(ALLOWED_JURISDICTIONS):
        if jurisdiction in name:
            jurisdiction_hits.append(jurisdiction)
    if "vendor" in name and "vendor_risk" not in domain_hits:
        domain_hits.append("vendor_risk")
    if "third_party" in name and "third_party_risk" not in domain_hits:
        domain_hits.append("third_party_risk")
    if "screening" in name and "transaction_screening" not in domain_hits:
        domain_hits.append("transaction_screening")
    if "hong" in name and "hong_kong" not in jurisdiction_hits:
        jurisdiction_hits.append("hong_kong")
    return {
        "domains": sorted(set(domain_hits)),
        "jurisdictions": sorted(set(jurisdiction_hits)),
    }


def build_dossier(case: CaseTarget, recovery_row: dict[str, Any] | None) -> dict[str, Any]:
    audit_context_path = case.case_dir / "audit_context.json"
    audit_context: dict[str, Any] = {}
    if audit_context_path.exists():
        try:
            audit_context = load_json(audit_context_path)
        except Exception:
            audit_context = {"_invalid_json": True}
    return {
        "case_dir": normalize_rel(case.case_dir),
        "case_name": case.case_dir.name,
        "issues": case.issue_messages,
        "audit_context_current": audit_context,
        "folder_name_hints": infer_folder_hints(case.case_dir),
        "taxonomy_recovery_context": recovery_row,
        "text_snippets": gather_text_snippets(case.case_dir),
        "decision_contract": {
            "required_fields": [
                "case_dir",
                "domains",
                "jurisdictions",
                "decided_by",
                "rationale",
                "evidence_refs",
            ],
            "allowed_domains": sorted(ALLOWED_DOMAINS),
            "allowed_jurisdictions": sorted(ALLOWED_JURISDICTIONS),
            "rules": [
                "do not guess",
                "do not infer beyond available case evidence",
                "do not invent outcomes",
                "use only explicit adjudication decisions",
                "domains and jurisdictions must be non-empty lists",
            ],
        },
    }


def render_dossier_md(dossier: dict[str, Any]) -> str:
    lines = [
        f"# Taxonomy Adjudication Dossier: {dossier['case_name']}",
        "",
        f"- case_dir: `{dossier['case_dir']}`",
        f"- issues: `{dossier['issues']}`",
        "",
        "## Folder Name Hints",
        "",
        f"- domains: `{dossier['folder_name_hints']['domains']}`",
        f"- jurisdictions: `{dossier['folder_name_hints']['jurisdictions']}`",
        "",
        "## Current Audit Context",
        "",
        "```json",
        json.dumps(dossier["audit_context_current"], indent=2),
        "```",
        "",
        "## Recovery Context",
        "",
        "```json",
        json.dumps(dossier["taxonomy_recovery_context"], indent=2),
        "```",
        "",
        "## Evidence Snippets",
        "",
    ]
    for row in dossier["text_snippets"]:
        lines.extend([
            f"### {row['path']}",
            "",
            "```text",
            row["snippet"],
            "```",
            "",
        ])
    lines.extend([
        "## Required Decision JSON Shape",
        "",
        "```json",
        json.dumps({
            "case_dir": dossier["case_dir"],
            "domains": ["..."],
            "jurisdictions": ["..."],
            "decided_by": "...",
            "rationale": "...",
            "evidence_refs": ["path/to/file", "other/file#section"],
        }, indent=2),
        "```",
        "",
    ])
    return "\n".join(lines)


def generate_dossiers(*, alignment_json: Path, recovery_json: Path, dossier_dir: Path) -> dict[str, Any]:
    targets = extract_targets_from_alignment(alignment_json)
    recovery_context = read_recovery_context(recovery_json)
    dossier_dir.mkdir(parents=True, exist_ok=True)

    dossiers: list[dict[str, Any]] = []
    for case in targets:
        recovery_row = recovery_context.get(normalize_rel(case.case_dir))
        dossier = build_dossier(case, recovery_row)
        dossier_json_path = dossier_dir / f"{case.case_dir.name}.dossier.json"
        dossier_md_path = dossier_dir / f"{case.case_dir.name}.dossier.md"
        atomic_write_json(dossier_json_path, dossier)
        atomic_write_text(dossier_md_path, render_dossier_md(dossier))
        dossiers.append({
            "case_dir": dossier["case_dir"],
            "dossier_json": normalize_rel(dossier_json_path),
            "dossier_md": normalize_rel(dossier_md_path),
        })

    summary = {
        "generated_at_epoch": int(time.time()),
        "dossier_count": len(dossiers),
        "dossiers": dossiers,
    }
    atomic_write_json(dossier_dir / "dossier_index.json", summary)
    return summary


def validate_decision(row: dict[str, Any]) -> Decision:
    case_dir = str(row.get("case_dir", "")).strip()
    decided_by = str(row.get("decided_by", "")).strip()
    rationale = str(row.get("rationale", "")).strip()
    domains = row.get("domains")
    jurisdictions = row.get("jurisdictions")
    evidence_refs = row.get("evidence_refs")

    if not case_dir:
        raise ValueError("decision missing case_dir")
    if not decided_by:
        raise ValueError(f"{case_dir}: missing decided_by")
    if not rationale:
        raise ValueError(f"{case_dir}: missing rationale")
    if not isinstance(domains, list) or not domains:
        raise ValueError(f"{case_dir}: domains must be non-empty list")
    if not isinstance(jurisdictions, list) or not jurisdictions:
        raise ValueError(f"{case_dir}: jurisdictions must be non-empty list")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        raise ValueError(f"{case_dir}: evidence_refs must be non-empty list")

    norm_domains: list[str] = []
    for item in domains:
        token = str(item).strip().lower()
        if token not in ALLOWED_DOMAINS:
            raise ValueError(f"{case_dir}: invalid domain `{token}`")
        norm_domains.append(token)

    norm_jurisdictions: list[str] = []
    for item in jurisdictions:
        token = str(item).strip().lower()
        if token not in ALLOWED_JURISDICTIONS:
            raise ValueError(f"{case_dir}: invalid jurisdiction `{token}`")
        norm_jurisdictions.append(token)

    refs = [str(item).strip() for item in evidence_refs if str(item).strip()]
    if not refs:
        raise ValueError(f"{case_dir}: evidence_refs must contain non-empty entries")

    return Decision(
        case_dir=case_dir,
        domains=norm_domains,
        jurisdictions=norm_jurisdictions,
        decided_by=decided_by,
        rationale=rationale,
        evidence_refs=refs,
    )


def ensure_backup(case_dir: Path, backup_root: Path) -> Path:
    backup_root.mkdir(parents=True, exist_ok=True)
    dest = backup_root / case_dir.name
    suffix = 1
    while dest.exists():
        dest = backup_root / f"{case_dir.name}_{suffix:03d}"
        suffix += 1
    shutil.copytree(case_dir, dest)
    return dest


def apply_decisions(
    *,
    decisions_json: Path,
    backup_root: Path,
    apply_report_json: Path,
    apply_report_md: Path,
    write: bool,
) -> dict[str, Any]:
    payload = load_json(decisions_json)
    rows = payload.get("decisions")
    if not isinstance(rows, list) or not rows:
        raise ValueError("decisions json must contain non-empty decisions array")

    decisions = [validate_decision(row) for row in rows]
    applied_rows: list[dict[str, Any]] = []

    for decision in decisions:
        case_dir = ROOT / safe_rel_path(decision.case_dir)
        audit_context_path = case_dir / "audit_context.json"
        if not audit_context_path.exists():
            raise FileNotFoundError(f"missing audit_context.json for {decision.case_dir}")

        audit_context = load_json(audit_context_path)
        if not isinstance(audit_context, dict):
            raise ValueError(f"audit_context.json must be object for {decision.case_dir}")

        before_domains = audit_context.get("domains")
        before_jurisdictions = audit_context.get("jurisdictions")
        backup_dir = None
        if write:
            backup_dir = ensure_backup(case_dir, backup_root)

        audit_context["domains"] = decision.domains
        audit_context["jurisdictions"] = decision.jurisdictions
        audit_context["taxonomy_adjudication"] = {
            "decided_by": decision.decided_by,
            "rationale": decision.rationale,
            "evidence_refs": decision.evidence_refs,
            "applied_at_epoch": int(time.time()),
        }

        if write:
            atomic_write_json(audit_context_path, audit_context)

        applied_rows.append({
            "case_dir": decision.case_dir,
            "before_domains": before_domains,
            "before_jurisdictions": before_jurisdictions,
            "after_domains": decision.domains,
            "after_jurisdictions": decision.jurisdictions,
            "decided_by": decision.decided_by,
            "backup_dir": normalize_rel(backup_dir) if backup_dir else None,
        })

    report = {
        "generated_at_epoch": int(time.time()),
        "mode": "write" if write else "dry_run",
        "applied_count": len(applied_rows),
        "applied": applied_rows,
    }
    atomic_write_json(apply_report_json, report)

    lines = [
        "# Taxonomy Adjudication Apply Report",
        "",
        f"- mode: `{report['mode']}`",
        f"- applied_count: `{report['applied_count']}`",
        "",
    ]
    for row in applied_rows:
        lines.extend([
            f"## {row['case_dir']}",
            f"- before_domains: `{row['before_domains']}`",
            f"- before_jurisdictions: `{row['before_jurisdictions']}`",
            f"- after_domains: `{row['after_domains']}`",
            f"- after_jurisdictions: `{row['after_jurisdictions']}`",
            f"- decided_by: `{row['decided_by']}`",
            f"- backup_dir: `{row['backup_dir']}`",
            "",
        ])
    atomic_write_text(apply_report_md, "\n".join(lines))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gold-case taxonomy adjudication workflow")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate-dossiers")
    gen.add_argument("--alignment-json", default=str(DEFAULT_ALIGNMENT_JSON))
    gen.add_argument("--recovery-json", default=str(DEFAULT_RECOVERY_JSON))
    gen.add_argument("--dossier-dir", default=str(DEFAULT_DOSSIER_DIR))

    apply_parser = sub.add_parser("apply-decisions")
    apply_parser.add_argument("--decisions-json", default=str(DEFAULT_DECISIONS_JSON))
    apply_parser.add_argument("--backup-root", default="logs/bible_alignment/taxonomy_adjudication_backups")
    apply_parser.add_argument("--apply-report-json", default=str(DEFAULT_APPLY_REPORT_JSON))
    apply_parser.add_argument("--apply-report-md", default=str(DEFAULT_APPLY_REPORT_MD))
    apply_parser.add_argument("--write", action="store_true")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "generate-dossiers":
        summary = generate_dossiers(
            alignment_json=Path(args.alignment_json),
            recovery_json=Path(args.recovery_json),
            dossier_dir=Path(args.dossier_dir),
        )
        print(json.dumps(summary, indent=2))
        return 0
    if args.command == "apply-decisions":
        report = apply_decisions(
            decisions_json=Path(args.decisions_json),
            backup_root=ROOT / args.backup_root,
            apply_report_json=Path(args.apply_report_json),
            apply_report_md=Path(args.apply_report_md),
            write=bool(args.write),
        )
        print(json.dumps(report, indent=2))
        return 0
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
