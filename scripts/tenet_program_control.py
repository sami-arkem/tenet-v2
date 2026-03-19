from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


ROOT = Path.cwd()

DEFAULT_OUTPUT_JSON = ROOT / "logs" / "program_control" / "program_control_report.json"
DEFAULT_OUTPUT_MD = ROOT / "logs" / "program_control" / "program_control_report.md"

PATHS = {
    "proof_density": ROOT / "logs" / "proof_density" / "proof_density_status.json",
    "final_execution": ROOT / "logs" / "final_execution_summary.json",
    "live_eval": ROOT / "logs" / "evals" / "live_model_eval_summary.json",
    "customer_pack_summary": ROOT / "logs" / "customer_pack_stability" / "summary.json",
    "bible_alignment": ROOT / "logs" / "bible_alignment" / "alignment_report.json",
    "taxonomy_recovery": ROOT / "logs" / "bible_alignment" / "taxonomy_recovery_report.json",
    "taxonomy_dossier_index": ROOT / "logs" / "bible_alignment" / "taxonomy_adjudication" / "dossier_index.json",
    "taxonomy_apply_report": ROOT / "logs" / "bible_alignment" / "taxonomy_adjudication_apply_report.json",
    "taxonomy_apply_report_v2": ROOT / "logs" / "bible_alignment" / "taxonomy_adjudication" / "apply_report.json",
    "real_002_readiness": ROOT / "logs" / "proof_density" / "proof_batch_real_002.readiness.json",
    "real_002_blocker_report": ROOT / "logs" / "proof_density" / "blocker_elimination" / "proof_batch_real_002" / "blocker_report.json",
    "real_002_orchestrator": ROOT / "logs" / "proof_density" / "execution" / "proof_batch_real_002" / "orchestrator_report.json",
}

TARGETS = {
    "gold_cases": 100,
    "customer_packs": 20,
}

WEIGHTS = {
    "proof_density": 30,
    "bible_alignment": 25,
    "workflow_integrity": 20,
    "customer_pack_stability": 10,
    "taxonomy_closure": 10,
    "intake_throughput": 5,
}


@dataclass(frozen=True)
class Blocker:
    code: str
    severity: str
    summary: str
    detail: str
    action: str


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


def load_json_if_exists(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def pct(numerator: int | float, denominator: int | float) -> float:
    if denominator <= 0:
        return 0.0
    return round((float(numerator) / float(denominator)) * 100.0, 2)


def get_proof_density_metrics() -> dict[str, Any]:
    payload = load_json_if_exists(PATHS["proof_density"])
    if not isinstance(payload, dict):
        return {
            "present": False,
            "gold_actual": None,
            "gold_target": TARGETS["gold_cases"],
            "packs_actual": None,
            "packs_target": TARGETS["customer_packs"],
            "gate_green": None,
        }
    gold_plan = payload.get("gold_cases", {}).get("gap_plan", {})
    pack_plan = payload.get("customer_packs", {}).get("gap_plan", {})
    gate_health = payload.get("gate_health", {})
    return {
        "present": True,
        "gold_actual": gold_plan.get("actual_total"),
        "gold_target": gold_plan.get("target_total", TARGETS["gold_cases"]),
        "packs_actual": pack_plan.get("actual_total"),
        "packs_target": pack_plan.get("target_total", TARGETS["customer_packs"]),
        "gate_green": gate_health.get("green"),
    }


def get_final_execution_metrics() -> dict[str, Any]:
    payload = load_json_if_exists(PATHS["final_execution"])
    if not isinstance(payload, dict):
        return {"present": False, "all_steps_passed": None}
    return {
        "present": True,
        "all_steps_passed": payload.get("all_steps_passed"),
    }


def get_live_eval_metrics() -> dict[str, Any]:
    payload = load_json_if_exists(PATHS["live_eval"])
    if payload is None:
        return {
            "present": False,
            "case_count": None,
            "failed_count": None,
            "min_weighted_score": None,
        }
    if isinstance(payload, list):
        failed_count = sum(1 for row in payload if not row.get("passed"))
        min_weighted = min((float(row.get("weighted_score", 0.0)) for row in payload), default=0.0)
        return {
            "present": True,
            "case_count": len(payload),
            "failed_count": failed_count,
            "min_weighted_score": min_weighted,
        }
    if isinstance(payload, dict):
        return {
            "present": True,
            "case_count": payload.get("case_count"),
            "failed_count": payload.get("failed_count"),
            "min_weighted_score": payload.get("min_weighted_score"),
        }
    return {
        "present": False,
        "case_count": None,
        "failed_count": None,
        "min_weighted_score": None,
    }


def get_customer_pack_metrics() -> dict[str, Any]:
    payload = load_json_if_exists(PATHS["customer_pack_summary"])
    if not isinstance(payload, dict):
        return {"present": False, "successful_runs": None}
    successful = payload.get("successful_workflow_runs")
    if successful is None:
        successful = payload.get("successful_runs")
    return {
        "present": True,
        "successful_runs": successful,
    }


def get_bible_alignment_metrics() -> dict[str, Any]:
    payload = load_json_if_exists(PATHS["bible_alignment"])
    if not isinstance(payload, dict):
        return {
            "present": False,
            "status": None,
            "issue_count": None,
            "error_count": None,
            "warning_count": None,
            "taxonomy_issue_count": None,
        }
    issues = payload.get("issues", [])
    error_count = 0
    warning_count = 0
    taxonomy_issue_count = 0
    for issue in issues:
        severity = issue.get("severity")
        message = str(issue.get("message", ""))
        if severity == "error":
            error_count += 1
        if severity == "warning":
            warning_count += 1
        if "domains must be a non-empty list" in message or "jurisdictions must be a non-empty list" in message:
            taxonomy_issue_count += 1
    return {
        "present": True,
        "status": payload.get("summary", {}).get("status"),
        "issue_count": payload.get("summary", {}).get("issue_count"),
        "error_count": error_count,
        "warning_count": warning_count,
        "taxonomy_issue_count": taxonomy_issue_count,
    }


def get_taxonomy_metrics() -> dict[str, Any]:
    dossier = load_json_if_exists(PATHS["taxonomy_dossier_index"])
    apply_report = load_json_if_exists(PATHS["taxonomy_apply_report_v2"])
    if not isinstance(apply_report, dict):
        apply_report = load_json_if_exists(PATHS["taxonomy_apply_report"])
    dossier_count = dossier.get("dossier_count") if isinstance(dossier, dict) else None
    applied_count = 0
    if isinstance(apply_report, dict):
        applied_count = int(apply_report.get("applied_count") or 0)
    unresolved = None
    if dossier_count is not None:
        unresolved = max(int(dossier_count) - applied_count, 0)
    return {
        "dossiers_present": isinstance(dossier, dict),
        "dossier_count": dossier_count,
        "adjudications_applied": applied_count,
        "unresolved_dossiers": unresolved,
    }


def get_real_002_metrics() -> dict[str, Any]:
    readiness = load_json_if_exists(PATHS["real_002_readiness"])
    blocker_report = load_json_if_exists(PATHS["real_002_blocker_report"])
    orchestrator = load_json_if_exists(PATHS["real_002_orchestrator"])
    ready_items = None
    blocked_items = None
    if isinstance(readiness, dict):
        counts = readiness.get("counts", {})
        ready_items = counts.get("ready_items")
        blocked_items = counts.get("blocked_items")
    imported_shards = None
    failed_shards = None
    if isinstance(orchestrator, dict):
        counts = orchestrator.get("counts", {})
        imported_shards = counts.get("imported_shards")
        failed_shards = counts.get("failed_shards")
    return {
        "readiness_present": isinstance(readiness, dict),
        "ready_items": ready_items,
        "blocked_items": blocked_items,
        "blocker_type_counts": blocker_report.get("blocker_type_counts") if isinstance(blocker_report, dict) else None,
        "imported_shards": imported_shards,
        "failed_shards": failed_shards,
    }


def compute_score(metrics: dict[str, Any]) -> dict[str, Any]:
    proof = metrics["proof_density"]
    bible = metrics["bible_alignment"]
    final_exec = metrics["final_execution"]
    live_eval = metrics["live_eval"]
    packs = metrics["customer_pack_summary"]
    taxonomy = metrics["taxonomy"]
    real_002 = metrics["real_002"]

    proof_density_score = 0.0
    if proof["gold_actual"] is not None and proof["packs_actual"] is not None:
        gold_ratio = min(float(proof["gold_actual"]) / float(proof["gold_target"]), 1.0)
        pack_ratio = min(float(proof["packs_actual"]) / float(proof["packs_target"]), 1.0)
        proof_density_score = round(((gold_ratio * 0.7) + (pack_ratio * 0.3)) * WEIGHTS["proof_density"], 2)

    bible_alignment_score = 0.0
    if bible["present"]:
        if bible["error_count"] == 0:
            bible_alignment_score = float(WEIGHTS["bible_alignment"])
        else:
            bible_alignment_score = round(max(0.0, WEIGHTS["bible_alignment"] * 0.15), 2)

    workflow_score = 0.0
    if final_exec["all_steps_passed"] is True and live_eval["failed_count"] in (None, 0):
        if live_eval["min_weighted_score"] is None or float(live_eval["min_weighted_score"]) >= 1.0:
            workflow_score = float(WEIGHTS["workflow_integrity"])

    pack_stability_score = 0.0
    if packs["successful_runs"] is not None:
        pack_stability_score = round(min(float(packs["successful_runs"]) / 20.0, 1.0) * WEIGHTS["customer_pack_stability"], 2)

    taxonomy_score = 0.0
    unresolved = taxonomy["unresolved_dossiers"]
    if unresolved is None:
        taxonomy_score = 0.0
    elif unresolved == 0:
        taxonomy_score = float(WEIGHTS["taxonomy_closure"])
    else:
        taxonomy_score = round(max(0.0, (1.0 - min(float(unresolved) / 10.0, 1.0))) * WEIGHTS["taxonomy_closure"], 2)

    intake_score = 0.0
    if real_002["ready_items"] is not None and real_002["blocked_items"] is not None:
        total = int(real_002["ready_items"]) + int(real_002["blocked_items"])
        if total > 0:
            intake_score = round((float(real_002["ready_items"]) / float(total)) * WEIGHTS["intake_throughput"], 2)

    total = round(
        proof_density_score
        + bible_alignment_score
        + workflow_score
        + pack_stability_score
        + taxonomy_score
        + intake_score,
        2,
    )
    return {
        "proof_density_score": proof_density_score,
        "bible_alignment_score": bible_alignment_score,
        "workflow_integrity_score": workflow_score,
        "customer_pack_stability_score": pack_stability_score,
        "taxonomy_closure_score": taxonomy_score,
        "intake_throughput_score": intake_score,
        "total_score": total,
    }


def build_blockers(metrics: dict[str, Any]) -> list[Blocker]:
    proof = metrics["proof_density"]
    bible = metrics["bible_alignment"]
    final_exec = metrics["final_execution"]
    live_eval = metrics["live_eval"]
    taxonomy = metrics["taxonomy"]
    real_002 = metrics["real_002"]
    blockers: list[Blocker] = []

    if proof["gold_actual"] is not None and proof["gold_actual"] < proof["gold_target"]:
        blockers.append(Blocker(
            code="proof.gold_cases_below_target",
            severity="high",
            summary=f"Gold cases below target: {proof['gold_actual']}/{proof['gold_target']}",
            detail="Proof density is not yet at the required corpus breadth.",
            action="Keep importing real corpus-backed gold cases until 100 is reached.",
        ))

    if proof["packs_actual"] is not None and proof["packs_actual"] < proof["packs_target"]:
        blockers.append(Blocker(
            code="proof.customer_packs_below_target",
            severity="high",
            summary=f"Customer packs below target: {proof['packs_actual']}/{proof['packs_target']}",
            detail="Enterprise workflow proof is not yet broad enough.",
            action="Add and stabilize more real customer evidence packs until 20 is reached.",
        ))

    if bible["error_count"] and bible["error_count"] > 0:
        blockers.append(Blocker(
            code="bible.alignment_errors_present",
            severity="critical",
            summary=f"Bible alignment errors present: {bible['error_count']}",
            detail="Repo still violates authoritative build-bible gates.",
            action="Resolve remaining bible gate errors before calling the corpus enterprise-ready.",
        ))

    if final_exec["all_steps_passed"] is not True:
        blockers.append(Blocker(
            code="workflow.final_execution_not_green",
            severity="critical",
            summary="Final execution discipline is not green",
            detail="End-to-end workflow integrity is not currently proven.",
            action="Restore final execution green and do not advance proof claims until fixed.",
        ))

    if live_eval["failed_count"] not in (None, 0):
        blockers.append(Blocker(
            code="eval.live_failures_present",
            severity="critical",
            summary=f"Live eval failures present: {live_eval['failed_count']}",
            detail="Deterministic/reporting behavior is not fully holding under eval.",
            action="Fix failing evals before adding more complexity.",
        ))

    if live_eval["min_weighted_score"] is not None and float(live_eval["min_weighted_score"]) < 1.0:
        blockers.append(Blocker(
            code="eval.weighted_score_below_1",
            severity="high",
            summary=f"Live eval min weighted score below 1.0: {live_eval['min_weighted_score']}",
            detail="The proof surface is below the current deterministic standard.",
            action="Investigate regression and restore full score.",
        ))

    if taxonomy["unresolved_dossiers"] not in (None, 0):
        blockers.append(Blocker(
            code="corpus.taxonomy_adjudications_unresolved",
            severity="high",
            summary=f"Unresolved taxonomy dossiers: {taxonomy['unresolved_dossiers']}",
            detail="Some gold cases still need explicit signed taxonomy decisions.",
            action="Fill config/gold_case_taxonomy_adjudications.json and apply decisions with backups.",
        ))

    if real_002["blocked_items"] not in (None, 0):
        blockers.append(Blocker(
            code="intake.real_002_blocked_items_present",
            severity="medium",
            summary=f"Blocked intake items in real_002: {real_002['blocked_items']}",
            detail="The current next proof batch is not yet importable.",
            action="Use repair files and blocker reports to convert blocked items into ready items.",
        ))

    return blockers


def build_worklist(metrics: dict[str, Any], blockers: list[Blocker]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    taxonomy = metrics["taxonomy"]
    real_002 = metrics["real_002"]
    proof = metrics["proof_density"]
    priority = 1

    if taxonomy["unresolved_dossiers"] not in (None, 0):
        tasks.append({
            "priority": priority,
            "task": "Resolve remaining gold-case taxonomy adjudications",
            "why": "Bible alignment cannot fully close while unresolved dossiers exist.",
            "exact_output": "Fill and apply config/gold_case_taxonomy_adjudications.json, then rerun bible gate.",
        })
        priority += 1

    if real_002["blocked_items"] not in (None, 0):
        tasks.append({
            "priority": priority,
            "task": "Convert blocked real_002 intake items into ready items",
            "why": "Proof throughput is currently constrained by blocked intake.",
            "exact_output": "Reduce blocked_items to 0 or at least produce a non-empty ready-only manifest.",
        })
        priority += 1

    if proof["gold_actual"] is not None and proof["gold_actual"] < proof["gold_target"]:
        tasks.append({
            "priority": priority,
            "task": "Import the next real gold-case batch",
            "why": "Gold proof corpus is below target.",
            "exact_output": f"Move from {proof['gold_actual']} toward {proof['gold_target']} gold cases without breaking gates.",
        })
        priority += 1

    if proof["packs_actual"] is not None and proof["packs_actual"] < proof["packs_target"]:
        tasks.append({
            "priority": priority,
            "task": "Import the next customer-pack batch",
            "why": "Enterprise operator proof is below target.",
            "exact_output": f"Move from {proof['packs_actual']} toward {proof['packs_target']} customer packs with green stability.",
        })
        priority += 1

    tasks.append({
        "priority": priority,
        "task": "Rerun proof-density + final execution after every corpus change",
        "why": "Current truth must stay authoritative and regression-free.",
        "exact_output": "Keep proof-density green and final execution green every run.",
    })
    return tasks


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Tenet Program Control Report",
        "",
        f"- generated_at_epoch: `{report['generated_at_epoch']}`",
        f"- enterprise_readiness_score: `{report['score']['total_score']}`",
        "",
        "## Score Breakdown",
        "",
    ]
    for key, value in report["score"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Metrics", ""])
    for section, payload in report["metrics"].items():
        lines.append(f"### {section}")
        for key, value in payload.items():
            lines.append(f"- {key}: `{value}`")
        lines.append("")
    lines.extend(["## Blockers", ""])
    for blocker in report["blockers"]:
        lines.append(f"- [{blocker['severity']}] `{blocker['code']}` - {blocker['summary']}")
        lines.append(f"  - detail: {blocker['detail']}")
        lines.append(f"  - action: {blocker['action']}")
    lines.extend(["", "## Worklist", ""])
    for row in report["worklist"]:
        lines.append(f"{row['priority']}. {row['task']}")
        lines.append(f"   - why: {row['why']}")
        lines.append(f"   - exact_output: {row['exact_output']}")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tenet program control gate")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metrics = {
        "proof_density": get_proof_density_metrics(),
        "final_execution": get_final_execution_metrics(),
        "live_eval": get_live_eval_metrics(),
        "customer_pack_summary": get_customer_pack_metrics(),
        "bible_alignment": get_bible_alignment_metrics(),
        "taxonomy": get_taxonomy_metrics(),
        "real_002": get_real_002_metrics(),
    }
    score = compute_score(metrics)
    blockers = build_blockers(metrics)
    worklist = build_worklist(metrics, blockers)
    report = {
        "generated_at_epoch": int(time.time()),
        "metrics": metrics,
        "score": score,
        "blockers": [
            {
                "code": blocker.code,
                "severity": blocker.severity,
                "summary": blocker.summary,
                "detail": blocker.detail,
                "action": blocker.action,
            }
            for blocker in blockers
        ],
        "worklist": worklist,
    }

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    atomic_write_json(output_json, report)
    atomic_write_text(output_md, render_markdown(report))

    print(json.dumps({
        "enterprise_readiness_score": score["total_score"],
        "blocker_count": len(blockers),
        "top_blocker": blockers[0].code if blockers else None,
        "worklist_count": len(worklist),
        "output_json": str(output_json),
        "output_md": str(output_md),
    }, indent=2))

    if args.strict and blockers:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
