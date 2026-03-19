from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

ROOT = Path.cwd()
DEFAULT_CONFIG_PATH = ROOT / "config" / "proof_density_targets.json"
STATUS_JSON_PATH = ROOT / "logs" / "proof_density" / "proof_density_status.json"
STATUS_MD_PATH = ROOT / "logs" / "proof_density" / "proof_density_status.md"

AUDIT_TYPE_DOMAIN_MAP = {
    "aml_readiness_review": ["aml", "governance"],
    "kyc_kyb_policy_and_control_review": ["kyc", "kyb", "governance"],
    "sanctions_readiness_review": ["sanctions", "transaction_screening", "governance"],
    "policy_governance_gap_analysis": ["governance", "remediation_tracking"],
    "vendor_internal_compliance_readiness_review": ["vendor_risk", "third_party_risk", "governance"],
    "fraud_readiness_review": ["fraud", "governance", "remediation_tracking"],
    "transaction_screening_review": ["transaction_screening", "sanctions", "governance"],
    "regulatory_licensing_readiness_review": ["regulatory_licensing", "governance"],
    "remediation_tracking_review": ["remediation_tracking", "governance"],
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


def load_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_slug(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def contains_unrecognized(items: list[str]) -> bool:
    return any(item.startswith("unrecognized:") for item in items)


def read_config(path: Path) -> dict[str, Any]:
    config = load_json(path)
    if config is None:
        raise FileNotFoundError(f"Missing config: {path}")
    return config


def find_existing_roots(paths: list[str]) -> list[Path]:
    roots: list[Path] = []
    for raw in paths:
        p = ROOT / raw
        if p.exists():
            roots.append(p)
    return roots


def iter_candidate_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    dirs: list[Path] = []
    if root.is_dir():
        dirs.append(root)
        dirs.extend([p for p in root.rglob("*") if p.is_dir()])
    return dirs


def find_manifest(base_dir: Path, manifest_names: list[str]) -> Path | None:
    for name in manifest_names:
        candidate = base_dir / name
        if candidate.exists():
            return candidate
    return None


def find_audit_context(base_dir: Path) -> Path | None:
    candidate = base_dir / "audit_context.json"
    return candidate if candidate.exists() else None


def file_count_under(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for p in path.rglob("*") if p.is_file())


@dataclass
class CorpusItem:
    kind: str
    item_id: str
    path: str
    manifest_path: str | None
    domain: str | None
    jurisdiction: str | None
    domains: list[str]
    jurisdictions: list[str]
    title: str | None
    source_type: str | None
    observed_files: int
    metadata_complete: bool
    metadata_issues: list[str]
    classification_key: str
    classification_keys: list[str]


def parse_manifest(manifest_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Invalid JSON manifest at {manifest_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Manifest must be a JSON object: {manifest_path}")
    return payload


def _normalize_domains(values: list[Any], allowed_domains: set[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            continue
        slug = normalize_slug(value)
        if slug == "kyc_kyb":
            normalized.extend(["kyc", "kyb"])
            continue
        normalized.append(slug if slug in allowed_domains else f"unrecognized:{slug}")
    return dedupe_keep_order(normalized)


def _normalize_jurisdictions(values: list[Any], allowed_jurisdictions: set[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            continue
        slug = normalize_slug(value)
        normalized.append(slug if slug in allowed_jurisdictions else f"unrecognized:{slug}")
    return dedupe_keep_order(normalized)


def _audit_context_payload(base_dir: Path) -> dict[str, Any]:
    audit_context_path = base_dir / "audit_context.json"
    if not audit_context_path.exists():
        return {}
    payload = load_json(audit_context_path)
    return payload if isinstance(payload, dict) else {}


def _extract_domains_and_jurisdictions(
    *,
    manifest: dict[str, Any],
    base_dir: Path,
    allowed_domains: set[str],
    allowed_jurisdictions: set[str],
) -> tuple[list[str], list[str]]:
    audit_context = _audit_context_payload(base_dir)

    raw_domains: list[Any] = []
    raw_jurisdictions: list[Any] = []

    if isinstance(manifest.get("domain"), str):
        raw_domains.append(manifest["domain"])
    raw_domains.extend(manifest.get("domains", []) or [])

    if isinstance(manifest.get("jurisdiction"), str):
        raw_jurisdictions.append(manifest["jurisdiction"])
    raw_jurisdictions.extend(manifest.get("jurisdictions", []) or [])

    if isinstance(audit_context.get("domain"), str):
        raw_domains.append(audit_context["domain"])
    raw_domains.extend(audit_context.get("domains", []) or [])

    if isinstance(audit_context.get("jurisdiction"), str):
        raw_jurisdictions.append(audit_context["jurisdiction"])
    raw_jurisdictions.extend(audit_context.get("jurisdictions", []) or [])

    domains = _normalize_domains(raw_domains, allowed_domains)
    jurisdictions = _normalize_jurisdictions(raw_jurisdictions, allowed_jurisdictions)

    if not domains:
        audit_type = manifest.get("audit_type") or audit_context.get("audit_type")
        if isinstance(audit_type, str):
            inferred = AUDIT_TYPE_DOMAIN_MAP.get(audit_type, [])
            domains = _normalize_domains(inferred, allowed_domains)

    return domains, jurisdictions


def classify_item(
    *,
    kind: str,
    base_dir: Path,
    manifest_path: Path | None,
    allowed_domains: set[str],
    allowed_jurisdictions: set[str],
) -> CorpusItem:
    manifest: dict[str, Any] = {}
    if manifest_path is not None:
        manifest = parse_manifest(manifest_path)
    audit_context = _audit_context_payload(base_dir)

    item_id = str(
        manifest.get("id")
        or manifest.get("audit_id")
        or manifest.get("case_id")
        or manifest.get("pack_id")
        or audit_context.get("audit_id")
        or audit_context.get("case_id")
        or base_dir.name
    )

    title = (
        manifest.get("title")
        or manifest.get("name")
        or audit_context.get("entity_name")
    )
    source_type = (
        manifest.get("source_type")
        or manifest.get("evidence_source_type")
        or audit_context.get("entity_type")
    )

    domains, jurisdictions = _extract_domains_and_jurisdictions(
        manifest=manifest,
        base_dir=base_dir,
        allowed_domains=allowed_domains,
        allowed_jurisdictions=allowed_jurisdictions,
    )

    domain = domains[0] if domains else None
    jurisdiction = jurisdictions[0] if jurisdictions else None
    metadata_issues: list[str] = []
    if not domains:
        metadata_issues.append("missing_domain")
    if not jurisdictions:
        metadata_issues.append("missing_jurisdiction")
    if contains_unrecognized(domains):
        metadata_issues.append("unrecognized_domain")
    if contains_unrecognized(jurisdictions):
        metadata_issues.append("unrecognized_jurisdiction")
    metadata_complete = not metadata_issues
    classification_keys = [
        f"{item_domain}::{item_jurisdiction}"
        for item_domain in domains
        for item_jurisdiction in jurisdictions
    ] or [f"{domain or 'unclassified'}::{jurisdiction or 'unclassified'}"]
    classification_key = classification_keys[0]

    return CorpusItem(
        kind=kind,
        item_id=item_id,
        path=str(base_dir),
        manifest_path=str(manifest_path) if manifest_path else None,
        domain=domain,
        jurisdiction=jurisdiction,
        domains=domains,
        jurisdictions=jurisdictions,
        title=title,
        source_type=source_type,
        observed_files=file_count_under(base_dir),
        metadata_complete=metadata_complete,
        metadata_issues=metadata_issues,
        classification_key=classification_key,
        classification_keys=classification_keys,
    )


def discover_items(
    *,
    kind: str,
    search_roots: list[str],
    manifest_names: list[str],
    allowed_domains: set[str],
    allowed_jurisdictions: set[str],
) -> list[CorpusItem]:
    items: list[CorpusItem] = []
    seen_paths: set[str] = set()
    claimed_roots: list[Path] = []

    for root in find_existing_roots(search_roots):
        for directory in iter_candidate_dirs(root):
            if kind == "customer_pack" and directory.name == "_template":
                continue
            if any(parent in directory.parents for parent in claimed_roots):
                continue

            audit_context_path = find_audit_context(directory)
            manifest_path = find_manifest(directory, manifest_names)

            # Prefer explicit audit-context units, then manifest-based detection.
            if audit_context_path is not None or manifest_path is not None:
                key = str(directory.resolve())
                if key in seen_paths:
                    continue
                seen_paths.add(key)
                claimed_roots.append(directory.resolve())
                items.append(
                    classify_item(
                        kind=kind,
                        base_dir=directory,
                        manifest_path=manifest_path,
                        allowed_domains=allowed_domains,
                        allowed_jurisdictions=allowed_jurisdictions,
                    )
                )
                continue

    items.sort(key=lambda x: (x.kind, x.domain or "", x.jurisdiction or "", x.item_id))
    return items


def run_command(name: str, argv: list[str], timeout_seconds: int) -> dict[str, Any]:
    cmd = [sys.executable, *argv]
    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env={**os.environ, "PYTHONPATH": "."},
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        duration = round(time.time() - started, 3)
        return {
            "name": name,
            "cmd": cmd,
            "returncode": proc.returncode,
            "timed_out": False,
            "duration_seconds": duration,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
            "passed": proc.returncode == 0,
        }
    except subprocess.TimeoutExpired as exc:
        duration = round(time.time() - started, 3)
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return {
            "name": name,
            "cmd": cmd,
            "returncode": None,
            "timed_out": True,
            "duration_seconds": duration,
            "stdout_tail": stdout[-4000:],
            "stderr_tail": stderr[-4000:],
            "passed": False,
        }


def summarize_distribution(items: list[CorpusItem]) -> dict[str, Any]:
    by_domain = Counter()
    by_jurisdiction = Counter()
    by_cell = Counter()
    unclassified: list[dict[str, Any]] = []

    for item in items:
        for domain in item.domains or [item.domain or "unclassified"]:
            by_domain[domain] += 1
        for jurisdiction in item.jurisdictions or [item.jurisdiction or "unclassified"]:
            by_jurisdiction[jurisdiction] += 1
        for classification_key in item.classification_keys or [item.classification_key]:
            by_cell[classification_key] += 1
        if not item.metadata_complete:
            unclassified.append(
                {
                    "item_id": item.item_id,
                    "path": item.path,
                    "manifest_path": item.manifest_path,
                    "kind": item.kind,
                    "metadata_issues": item.metadata_issues,
                }
            )

    return {
        "by_domain": dict(sorted(by_domain.items())),
        "by_jurisdiction": dict(sorted(by_jurisdiction.items())),
        "by_cell": dict(sorted(by_cell.items())),
        "unclassified_items": unclassified,
    }


def compute_gap_plan(
    *,
    items: list[CorpusItem],
    allowed_domains: list[str],
    allowed_jurisdictions: list[str],
    target_total: int,
) -> dict[str, Any]:
    actual_total = len(items)
    remaining_to_target = max(target_total - actual_total, 0)

    by_cell = Counter(
        classification_key
        for item in items
        if item.metadata_complete
        for classification_key in item.classification_keys
    )

    expected_cells = [f"{d}::{j}" for d in allowed_domains for j in allowed_jurisdictions]
    cell_gaps: list[dict[str, Any]] = []

    for cell in expected_cells:
        current = by_cell.get(cell, 0)
        # First priority is zero-coverage cells, then thin cells.
        priority = 0
        if current == 0:
            priority = 100
        elif current == 1:
            priority = 80
        elif current == 2:
            priority = 60
        elif current == 3:
            priority = 40
        else:
            priority = 0

        domain, jurisdiction = cell.split("::", 1)
        cell_gaps.append(
            {
                "domain": domain,
                "jurisdiction": jurisdiction,
                "current_count": current,
                "priority": priority,
            }
        )

    cell_gaps.sort(key=lambda x: (-x["priority"], x["current_count"], x["domain"], x["jurisdiction"]))

    recommended_next_batch = []
    for row in cell_gaps:
        if row["priority"] <= 0:
            continue
        recommended_next_batch.append(
            {
                "domain": row["domain"],
                "jurisdiction": row["jurisdiction"],
                "add_count": 1 if row["current_count"] == 0 else 1,
                "reason": "zero_coverage" if row["current_count"] == 0 else "thin_coverage",
            }
        )
        if len(recommended_next_batch) >= min(10, remaining_to_target):
            break

    return {
        "actual_total": actual_total,
        "target_total": target_total,
        "remaining_to_target": remaining_to_target,
        "recommended_next_batch": recommended_next_batch,
        "cell_gaps": cell_gaps[:50],
    }


def load_observed_gate_artifacts() -> dict[str, Any]:
    final_summary = load_json(ROOT / "logs" / "final_execution_summary.json")
    live_eval = load_json(ROOT / "logs" / "evals" / "live_model_eval_summary.json")
    customer_pack_summary = load_json(ROOT / "logs" / "customer_pack_stability" / "summary.json")
    readiness = load_json(ROOT / "logs" / "customer_pack_stability" / "readiness_after_customer_stability.json")

    eval_case_count = None
    eval_failed_count = None
    eval_min_weighted_score = None
    if isinstance(live_eval, list):
        eval_case_count = len(live_eval)
        eval_failed_count = sum(1 for row in live_eval if not row.get("passed"))
        eval_min_weighted_score = min(
            (row.get("weighted_score", 0.0) for row in live_eval),
            default=0.0,
        )
    elif isinstance(live_eval, dict):
        eval_case_count = live_eval.get("case_count")
        eval_failed_count = live_eval.get("failed_count")
        eval_min_weighted_score = live_eval.get("min_weighted_score")
    elif isinstance(final_summary, dict):
        final_eval = final_summary.get("eval") or {}
        eval_case_count = final_eval.get("case_count")
        eval_failed_count = final_eval.get("failed_count")
        eval_min_weighted_score = final_eval.get("min_weighted_score")

    if readiness is None and isinstance(final_summary, dict):
        readiness = final_summary.get("readiness")
    if customer_pack_summary is None and isinstance(final_summary, dict):
        customer_pack_summary = final_summary.get("customer_pack_stability")

    customer_pack_successful_runs = None
    if isinstance(customer_pack_summary, dict):
        if "successful_workflow_runs" in customer_pack_summary:
            customer_pack_successful_runs = customer_pack_summary.get("successful_workflow_runs")
        else:
            customer_pack_successful_runs = customer_pack_summary.get("successful_runs")

    observed: dict[str, Any] = {
        "final_execution_summary_present": final_summary is not None,
        "live_model_eval_summary_present": live_eval is not None,
        "customer_pack_summary_present": customer_pack_summary is not None,
        "readiness_summary_present": readiness is not None,
        "all_steps_passed": final_summary.get("all_steps_passed") if final_summary else None,
        "eval_case_count": eval_case_count,
        "eval_failed_count": eval_failed_count,
        "eval_min_weighted_score": eval_min_weighted_score,
        "customer_pack_successful_runs": customer_pack_successful_runs,
        "overall_readiness": readiness.get("overall_readiness") if readiness else None,
    }
    return observed


def compute_overall_gate_health(
    *,
    gate_results: list[dict[str, Any]],
    observed_artifacts: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    ran_final_execution = next(
        (step for step in gate_results if step["name"] == "final_execution_discipline"),
        None,
    )

    for step in gate_results:
        if not step["passed"]:
            if step["timed_out"]:
                failures.append(f'{step["name"]}: timed out')
            else:
                failures.append(f'{step["name"]}: returncode={step["returncode"]}')

    if observed_artifacts.get("all_steps_passed") is False and not (
        ran_final_execution and ran_final_execution["passed"]
    ):
        failures.append("logs/final_execution_summary.json reports all_steps_passed=false")

    eval_failed_count = observed_artifacts.get("eval_failed_count")
    if eval_failed_count not in (None, 0):
        failures.append(f"live eval failed_count={eval_failed_count}")

    eval_min_weighted_score = observed_artifacts.get("eval_min_weighted_score")
    if eval_min_weighted_score is not None:
        try:
            if float(eval_min_weighted_score) < 1.0:
                failures.append(f"live eval min_weighted_score={eval_min_weighted_score}")
        except Exception:
            failures.append(f"live eval min_weighted_score invalid={eval_min_weighted_score}")

    return {
        "green": len(failures) == 0,
        "failures": failures,
    }


def render_markdown(status: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Tenet Proof Density Status")
    lines.append("")
    lines.append(f"- generated_at_epoch: `{status['generated_at_epoch']}`")
    lines.append(f"- overall_gate_green: `{status['gate_health']['green']}`")
    lines.append(f"- gold_cases: `{status['gold_cases']['gap_plan']['actual_total']}/{status['gold_cases']['gap_plan']['target_total']}`")
    lines.append(f"- customer_packs: `{status['customer_packs']['gap_plan']['actual_total']}/{status['customer_packs']['gap_plan']['target_total']}`")
    lines.append("")

    lines.append("## Observed Gate Artifacts")
    lines.append("")
    for k, v in status["observed_gate_artifacts"].items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")

    lines.append("## Gate Results")
    lines.append("")
    for step in status["gate_results"]:
        lines.append(
            f"- {step['name']}: passed=`{step['passed']}` timed_out=`{step['timed_out']}` "
            f"returncode=`{step['returncode']}` duration_seconds=`{step['duration_seconds']}`"
        )
    lines.append("")

    lines.append("## Gold Case Next Batch")
    lines.append("")
    for row in status["gold_cases"]["gap_plan"]["recommended_next_batch"]:
        lines.append(
            f"- add 1 gold case: domain=`{row['domain']}` jurisdiction=`{row['jurisdiction']}` reason=`{row['reason']}`"
        )
    if not status["gold_cases"]["gap_plan"]["recommended_next_batch"]:
        lines.append("- no gap recommendation available")
    lines.append("")

    lines.append("## Customer Pack Next Batch")
    lines.append("")
    for row in status["customer_packs"]["gap_plan"]["recommended_next_batch"]:
        lines.append(
            f"- add 1 customer pack: domain=`{row['domain']}` jurisdiction=`{row['jurisdiction']}` reason=`{row['reason']}`"
        )
    if not status["customer_packs"]["gap_plan"]["recommended_next_batch"]:
        lines.append("- no gap recommendation available")
    lines.append("")

    unclassified_gold = status["gold_cases"]["distribution"]["unclassified_items"]
    unclassified_packs = status["customer_packs"]["distribution"]["unclassified_items"]

    lines.append("## Metadata Debt")
    lines.append("")
    lines.append(f"- unclassified_gold_cases: `{len(unclassified_gold)}`")
    lines.append(f"- unclassified_customer_packs: `{len(unclassified_packs)}`")
    lines.append("")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic Tenet proof-density lane")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--skip-gates", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = read_config(Path(args.config))

    allowed_domains = [normalize_slug(x) for x in config["allowed_domains"]]
    allowed_jurisdictions = [normalize_slug(x) for x in config["allowed_jurisdictions"]]
    allowed_domain_set = set(allowed_domains)
    allowed_jurisdiction_set = set(allowed_jurisdictions)

    gold_cases = discover_items(
        kind="gold_case",
        search_roots=config["gold_case_search_roots"],
        manifest_names=config["gold_case_manifest_names"],
        allowed_domains=allowed_domain_set,
        allowed_jurisdictions=allowed_jurisdiction_set,
    )
    customer_packs = discover_items(
        kind="customer_pack",
        search_roots=config["customer_pack_search_roots"],
        manifest_names=config["customer_pack_manifest_names"],
        allowed_domains=allowed_domain_set,
        allowed_jurisdictions=allowed_jurisdiction_set,
    )

    gate_results: list[dict[str, Any]] = []
    if not args.skip_gates:
        for step in config["gate_commands"]:
            if not step.get("enabled", True):
                continue
            gate_results.append(
                run_command(
                    name=step["name"],
                    argv=step["argv"],
                    timeout_seconds=int(step["timeout_seconds"]),
                )
            )

    observed_gate_artifacts = load_observed_gate_artifacts()

    gold_case_gap_plan = compute_gap_plan(
        items=gold_cases,
        allowed_domains=allowed_domains,
        allowed_jurisdictions=allowed_jurisdictions,
        target_total=int(config["targets"]["gold_cases_target"]),
    )
    customer_pack_gap_plan = compute_gap_plan(
        items=customer_packs,
        allowed_domains=allowed_domains,
        allowed_jurisdictions=allowed_jurisdictions,
        target_total=int(config["targets"]["customer_packs_target"]),
    )

    status = {
        "version": "v1",
        "generated_at_epoch": int(time.time()),
        "config_path": str(Path(args.config)),
        "observed_gate_artifacts": observed_gate_artifacts,
        "gate_results": gate_results,
        "gold_cases": {
            "items": [item.__dict__ for item in gold_cases],
            "distribution": summarize_distribution(gold_cases),
            "gap_plan": gold_case_gap_plan,
        },
        "customer_packs": {
            "items": [item.__dict__ for item in customer_packs],
            "distribution": summarize_distribution(customer_packs),
            "gap_plan": customer_pack_gap_plan,
        },
    }

    gate_health = compute_overall_gate_health(
        gate_results=gate_results,
        observed_artifacts=observed_gate_artifacts,
    )
    status["gate_health"] = gate_health

    atomic_write_json(STATUS_JSON_PATH, status)
    atomic_write_text(STATUS_MD_PATH, render_markdown(status))

    print(json.dumps(
        {
            "proof_density_status_path": str(STATUS_JSON_PATH),
            "proof_density_markdown_path": str(STATUS_MD_PATH),
            "gate_green": gate_health["green"],
            "gold_cases_actual": gold_case_gap_plan["actual_total"],
            "gold_cases_target": gold_case_gap_plan["target_total"],
            "gold_cases_remaining": gold_case_gap_plan["remaining_to_target"],
            "customer_packs_actual": customer_pack_gap_plan["actual_total"],
            "customer_packs_target": customer_pack_gap_plan["target_total"],
            "customer_packs_remaining": customer_pack_gap_plan["remaining_to_target"],
            "recommended_next_gold_batch": gold_case_gap_plan["recommended_next_batch"],
            "recommended_next_customer_pack_batch": customer_pack_gap_plan["recommended_next_batch"],
            "failures": gate_health["failures"],
        },
        indent=2
    ))

    if args.strict and not gate_health["green"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
