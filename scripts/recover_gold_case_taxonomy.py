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
DEFAULT_RULES_PATH = ROOT / "config" / "tenet_build_bible_rules.json"
DEFAULT_REPORT_JSON = ROOT / "logs" / "bible_alignment" / "taxonomy_recovery_report.json"
DEFAULT_REPORT_MD = ROOT / "logs" / "bible_alignment" / "taxonomy_recovery_report.md"

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

DOMAIN_ALIASES = {
    "aml": "aml",
    "anti_money_laundering": "aml",
    "kyc": "kyc",
    "kyb": "kyb",
    "sanctions": "sanctions",
    "governance": "governance",
    "vendor": "vendor_risk",
    "vendor_risk": "vendor_risk",
    "third_party": "third_party_risk",
    "third_party_risk": "third_party_risk",
    "fraud": "fraud",
    "transaction_screening": "transaction_screening",
    "screening": "transaction_screening",
    "regulatory_reporting": "regulatory_reporting",
    "reporting": "regulatory_reporting",
    "regulatory_licensing": "regulatory_licensing",
    "licensing": "regulatory_licensing",
    "remediation": "remediation_tracking",
    "remediation_tracking": "remediation_tracking",
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

JURISDICTION_ALIASES = {
    "global": "global",
    "eu": "eu",
    "uk": "uk",
    "us": "us",
    "usa": "us",
    "uae": "uae",
    "singapore": "singapore",
    "india": "india",
    "hong_kong": "hong_kong",
    "hongkong": "hong_kong",
    "canada": "canada",
    "australia": "australia",
}

TEXT_EXTENSIONS = {".json", ".md", ".txt", ".yaml", ".yml"}


@dataclass(frozen=True)
class Candidate:
    value: str
    source: str
    confidence: int


@dataclass(frozen=True)
class RecoveryResult:
    case_dir: str
    changed: bool
    blocked: bool
    domain_before: list[str] | None
    jurisdiction_before: list[str] | None
    domain_after: list[str] | None
    jurisdiction_after: list[str] | None
    reasons: list[str]
    backup_dir: str | None


def normalize(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


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


def discover_gold_case_roots(rules: dict[str, Any]) -> list[Path]:
    roots: list[Path] = []
    for rel in rules.get("gold_case_roots", []):
        path = ROOT / rel
        if path.exists():
            roots.append(path)
    return roots


def discover_case_dirs(gold_case_roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()
    for root in gold_case_roots:
        for candidate in sorted(p for p in root.iterdir() if p.is_dir()):
            if (candidate / "audit_context.json").exists():
                key = str(candidate.resolve())
                if key not in seen:
                    seen.add(key)
                    out.append(candidate)
    return out


def normalize_token(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("&", "and")
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )


def canonical_domain(value: str) -> str | None:
    return DOMAIN_ALIASES.get(normalize_token(value))


def canonical_jurisdiction(value: str) -> str | None:
    return JURISDICTION_ALIASES.get(normalize_token(value))


def read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = load_json(path)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def extract_from_folder_name(case_dir: Path) -> tuple[list[Candidate], list[Candidate]]:
    tokens = [normalize_token(x) for x in case_dir.name.split("_") if x.strip()]
    domains: list[Candidate] = []
    jurisdictions: list[Candidate] = []
    for token in tokens:
        domain = canonical_domain(token)
        jurisdiction = canonical_jurisdiction(token)
        if domain:
            domains.append(Candidate(domain, "folder_name", 80))
        if jurisdiction:
            jurisdictions.append(Candidate(jurisdiction, "folder_name", 80))
    for idx in range(len(tokens) - 1):
        joined = f"{tokens[idx]}_{tokens[idx + 1]}"
        domain = canonical_domain(joined)
        jurisdiction = canonical_jurisdiction(joined)
        if domain:
            domains.append(Candidate(domain, "folder_name_joined", 90))
        if jurisdiction:
            jurisdictions.append(Candidate(jurisdiction, "folder_name_joined", 90))
    return domains, jurisdictions


def _scan_json_obj(obj: Any, source_name: str, domains: list[Candidate], jurisdictions: list[Candidate]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_norm = normalize_token(str(key))
            if key_norm in {"domain", "domains", "audit_type", "source_families"}:
                if isinstance(value, str):
                    domain = canonical_domain(value)
                    if domain:
                        domains.append(Candidate(domain, source_name, 95 if key_norm in {"domain", "domains"} else 85))
                elif isinstance(value, list):
                    for item in value:
                        domain = canonical_domain(str(item))
                        if domain:
                            domains.append(Candidate(domain, source_name, 95 if key_norm in {"domain", "domains"} else 85))
            if key_norm in {"jurisdiction", "jurisdictions"}:
                if isinstance(value, str):
                    jurisdiction = canonical_jurisdiction(value)
                    if jurisdiction:
                        jurisdictions.append(Candidate(jurisdiction, source_name, 95))
                elif isinstance(value, list):
                    for item in value:
                        jurisdiction = canonical_jurisdiction(str(item))
                        if jurisdiction:
                            jurisdictions.append(Candidate(jurisdiction, source_name, 95))
            if isinstance(value, (dict, list)):
                _scan_json_obj(value, source_name, domains, jurisdictions)
            elif isinstance(value, str):
                domain = canonical_domain(value)
                jurisdiction = canonical_jurisdiction(value)
                if domain:
                    domains.append(Candidate(domain, source_name, 35))
                if jurisdiction:
                    jurisdictions.append(Candidate(jurisdiction, source_name, 35))
    elif isinstance(obj, list):
        for item in obj:
            _scan_json_obj(item, source_name, domains, jurisdictions)


def extract_from_known_json(case_dir: Path) -> tuple[list[Candidate], list[Candidate]]:
    domains: list[Candidate] = []
    jurisdictions: list[Candidate] = []
    candidate_files = [
        case_dir / "audit_context.json",
        case_dir / "source_manifest.json",
        case_dir / "evidence_index.json",
        case_dir / "expected_assertions.json",
        case_dir / "expected_outcome.json",
    ]
    for path in candidate_files:
        payload = read_json_if_exists(path)
        if payload is not None:
            _scan_json_obj(payload, normalize(path), domains, jurisdictions)
    return domains, jurisdictions


def extract_from_text(case_dir: Path) -> tuple[list[Candidate], list[Candidate]]:
    domains: list[Candidate] = []
    jurisdictions: list[Candidate] = []
    for path in sorted(p for p in case_dir.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_EXTENSIONS):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        lowered = normalize_token(text)
        for raw, canonical in DOMAIN_ALIASES.items():
            if raw in lowered:
                domains.append(Candidate(canonical, normalize(path), 20))
        for raw, canonical in JURISDICTION_ALIASES.items():
            if raw in lowered:
                jurisdictions.append(Candidate(canonical, normalize(path), 20))
    return domains, jurisdictions


def summarize_candidates(candidates: list[Candidate]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        row = summary.setdefault(candidate.value, {"max_confidence": 0, "sources": []})
        row["max_confidence"] = max(row["max_confidence"], candidate.confidence)
        row["sources"].append(candidate.source)
    for value in summary:
        summary[value]["sources"] = sorted(set(summary[value]["sources"]))
    return summary


def choose_values(candidates: list[Candidate], allowed: set[str], minimum_confidence: int) -> tuple[list[str] | None, list[str]]:
    reasons: list[str] = []
    if not candidates:
        return None, ["no candidates found"]
    summary = summarize_candidates([candidate for candidate in candidates if candidate.value in allowed])
    if not summary:
        return None, ["no allowed candidates found"]
    ranked = sorted(summary.items(), key=lambda item: (-item[1]["max_confidence"], item[0]))
    best_value, best_meta = ranked[0]
    if best_meta["max_confidence"] < minimum_confidence:
        return None, [f"best candidate below confidence threshold: {best_value} @ {best_meta['max_confidence']}"]
    tied = [value for value, meta in ranked if meta["max_confidence"] == best_meta["max_confidence"]]
    if len(tied) > 1:
        return None, [f"ambiguous top candidates at same confidence: {tied}"]
    reasons.append(f"selected {best_value} from {best_meta['sources']} @ {best_meta['max_confidence']}")
    return [best_value], reasons


def ensure_backup(case_dir: Path, backup_root: Path) -> Path:
    backup_root.mkdir(parents=True, exist_ok=True)
    destination = backup_root / case_dir.name
    suffix = 1
    while destination.exists():
        destination = backup_root / f"{case_dir.name}_{suffix:03d}"
        suffix += 1
    shutil.copytree(case_dir, destination)
    return destination


def recover_case(*, case_dir: Path, backup_root: Path, minimum_confidence: int, write: bool) -> RecoveryResult:
    audit_context_path = case_dir / "audit_context.json"
    try:
        payload = load_json(audit_context_path)
    except Exception as exc:
        return RecoveryResult(
            case_dir=normalize(case_dir),
            changed=False,
            blocked=True,
            domain_before=None,
            jurisdiction_before=None,
            domain_after=None,
            jurisdiction_after=None,
            reasons=[f"invalid audit_context.json: {exc}"],
            backup_dir=None,
        )
    if not isinstance(payload, dict):
        return RecoveryResult(
            case_dir=normalize(case_dir),
            changed=False,
            blocked=True,
            domain_before=None,
            jurisdiction_before=None,
            domain_after=None,
            jurisdiction_after=None,
            reasons=["audit_context.json must be an object"],
            backup_dir=None,
        )

    reasons: list[str] = []
    domain_before = payload.get("domains") if isinstance(payload.get("domains"), list) else None
    jurisdiction_before = payload.get("jurisdictions") if isinstance(payload.get("jurisdictions"), list) else None
    missing_domain = not isinstance(domain_before, list) or not domain_before
    missing_jurisdiction = not isinstance(jurisdiction_before, list) or not jurisdiction_before

    if not missing_domain and not missing_jurisdiction:
        return RecoveryResult(
            case_dir=normalize(case_dir),
            changed=False,
            blocked=False,
            domain_before=domain_before,
            jurisdiction_before=jurisdiction_before,
            domain_after=domain_before,
            jurisdiction_after=jurisdiction_before,
            reasons=["taxonomy already present"],
            backup_dir=None,
        )

    folder_domains, folder_jurisdictions = extract_from_folder_name(case_dir)
    json_domains, json_jurisdictions = extract_from_known_json(case_dir)
    text_domains, text_jurisdictions = extract_from_text(case_dir)
    all_domains = [*folder_domains, *json_domains, *text_domains]
    all_jurisdictions = [*folder_jurisdictions, *json_jurisdictions, *text_jurisdictions]

    domain_after = list(domain_before) if isinstance(domain_before, list) else None
    jurisdiction_after = list(jurisdiction_before) if isinstance(jurisdiction_before, list) else None
    blocked = False

    if missing_domain:
        chosen_domain, domain_reasons = choose_values(all_domains, ALLOWED_DOMAINS, minimum_confidence)
        reasons.extend([f"domain: {reason}" for reason in domain_reasons])
        if chosen_domain is None:
            blocked = True
        else:
            domain_after = chosen_domain

    if missing_jurisdiction:
        chosen_jurisdiction, jurisdiction_reasons = choose_values(all_jurisdictions, ALLOWED_JURISDICTIONS, minimum_confidence)
        reasons.extend([f"jurisdiction: {reason}" for reason in jurisdiction_reasons])
        if chosen_jurisdiction is None:
            blocked = True
        else:
            jurisdiction_after = chosen_jurisdiction

    changed = (domain_after != domain_before) or (jurisdiction_after != jurisdiction_before)
    backup_dir: Path | None = None
    if write and changed and not blocked:
        backup_dir = ensure_backup(case_dir, backup_root)
        payload["domains"] = domain_after
        payload["jurisdictions"] = jurisdiction_after
        atomic_write_json(audit_context_path, payload)

    return RecoveryResult(
        case_dir=normalize(case_dir),
        changed=changed and not blocked,
        blocked=blocked,
        domain_before=domain_before,
        jurisdiction_before=jurisdiction_before,
        domain_after=domain_after,
        jurisdiction_after=jurisdiction_after,
        reasons=reasons,
        backup_dir=normalize(backup_dir) if backup_dir else None,
    )


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Gold Case Taxonomy Recovery Report",
        "",
        f"- generated_at_epoch: `{report['generated_at_epoch']}`",
        f"- mode: `{report['mode']}`",
        f"- total_cases: `{report['summary']['total_cases']}`",
        f"- recoverable_count: `{report['summary']['recoverable_count']}`",
        f"- blocked_count: `{report['summary']['blocked_count']}`",
        f"- already_complete_count: `{report['summary']['already_complete_count']}`",
        "",
        "## Cases",
        "",
    ]
    for row in report["cases"]:
        lines.append(f"### {row['case_dir']}")
        lines.append(f"- changed: `{row['changed']}`")
        lines.append(f"- blocked: `{row['blocked']}`")
        lines.append(f"- domain_before: `{row['domain_before']}`")
        lines.append(f"- jurisdiction_before: `{row['jurisdiction_before']}`")
        lines.append(f"- domain_after: `{row['domain_after']}`")
        lines.append(f"- jurisdiction_after: `{row['jurisdiction_after']}`")
        if row["backup_dir"]:
            lines.append(f"- backup_dir: `{row['backup_dir']}`")
        lines.append("- reasons:")
        for reason in row["reasons"]:
            lines.append(f"  - {reason}")
        lines.append("")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recover missing gold-case taxonomy from existing evidence only")
    parser.add_argument("--rules", default=str(DEFAULT_RULES_PATH))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    parser.add_argument("--backup-root", default="logs/bible_alignment/taxonomy_recovery_backups")
    parser.add_argument("--minimum-confidence", type=int, default=70)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rules = load_json(Path(args.rules))
    roots = discover_gold_case_roots(rules)
    if not roots:
        raise SystemExit("No gold case roots found")
    case_dirs = discover_case_dirs(roots)
    backup_root = ROOT / args.backup_root
    results = [
        recover_case(
            case_dir=case_dir,
            backup_root=backup_root,
            minimum_confidence=int(args.minimum_confidence),
            write=bool(args.write),
        )
        for case_dir in case_dirs
    ]

    recoverable_count = sum(1 for result in results if result.changed)
    blocked_count = sum(1 for result in results if result.blocked)
    already_complete_count = sum(1 for result in results if (not result.changed and not result.blocked))

    report = {
        "version": "v1",
        "generated_at_epoch": int(time.time()),
        "mode": "write" if args.write else "dry_run",
        "summary": {
            "total_cases": len(results),
            "recoverable_count": recoverable_count,
            "blocked_count": blocked_count,
            "already_complete_count": already_complete_count,
        },
        "cases": [
            {
                "case_dir": result.case_dir,
                "changed": result.changed,
                "blocked": result.blocked,
                "domain_before": result.domain_before,
                "jurisdiction_before": result.jurisdiction_before,
                "domain_after": result.domain_after,
                "jurisdiction_after": result.jurisdiction_after,
                "reasons": result.reasons,
                "backup_dir": result.backup_dir,
            }
            for result in results
        ],
    }

    atomic_write_json(Path(args.report_json), report)
    atomic_write_text(Path(args.report_md), render_markdown(report))

    print(json.dumps({
        "mode": report["mode"],
        "total_cases": report["summary"]["total_cases"],
        "recoverable_count": report["summary"]["recoverable_count"],
        "blocked_count": report["summary"]["blocked_count"],
        "already_complete_count": report["summary"]["already_complete_count"],
        "report_json": str(Path(args.report_json)),
        "report_md": str(Path(args.report_md)),
    }, indent=2))

    if args.strict and blocked_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
