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

DEFAULT_PLAN_JSON = ROOT / "config" / "proof_batch_real_002.plan.json"
DEFAULT_READINESS_JSON = ROOT / "logs" / "proof_density" / "proof_batch_real_002.readiness.json"
DEFAULT_OUTPUT_DIR = ROOT / "logs" / "proof_density" / "execution"
DEFAULT_BATCH_MANIFEST_DIR = ROOT / "config" / "generated_batches"

INTAKE_MANAGER = ROOT / "scripts" / "proof_intake_manager.py"
BATCH_IMPORTER = ROOT / "scripts" / "proof_batch_import.py"
PROOF_DENSITY = ROOT / "scripts" / "proof_density_lane.py"
FINAL_EXECUTION = ROOT / "scripts" / "final_execution_discipline.py"


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


def load_json(path: Path) -> Any:
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


def run_cmd(argv: list[str], timeout_seconds: int) -> dict[str, Any]:
    started = time.time()
    try:
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
            "timed_out": False,
            "duration_seconds": round(time.time() - started, 3),
            "stdout_tail": proc.stdout[-12000:],
            "stderr_tail": proc.stderr[-12000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": argv,
            "returncode": 124,
            "passed": False,
            "timed_out": True,
            "duration_seconds": round(time.time() - started, 3),
            "stdout_tail": (exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": ((exc.stderr or "") + "\nTimed out.")[-12000:] if isinstance(exc.stderr, str) else "Timed out.",
        }


@dataclass(frozen=True)
class PlannedItem:
    kind: str
    item_id: str
    title: str
    source_dir: str
    domains: list[str]
    jurisdictions: list[str]
    reason: str


@dataclass(frozen=True)
class ReadinessItem:
    kind: str
    item_id: str
    title: str
    source_dir: str
    domains: list[str]
    jurisdictions: list[str]
    reason: str
    ready: bool
    readiness_score: float
    missing_required: list[str]
    validation_errors: list[str]
    placeholder_findings: list[str]


def parse_plan(plan_json: Path) -> tuple[str, list[PlannedItem]]:
    payload = load_json(plan_json)
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError(f"Plan missing items: {plan_json}")

    batch_label = str(payload.get("batch_label", "proof_batch")).strip()
    out: list[PlannedItem] = []

    for idx, raw in enumerate(items):
        if not isinstance(raw, dict):
            raise ValueError(f"Plan item {idx} must be object")
        out.append(
            PlannedItem(
                kind=str(raw["kind"]),
                item_id=normalize_slug(str(raw["id"])),
                title=str(raw["title"]),
                source_dir=str(raw["source_dir"]),
                domains=[normalize_slug(str(x)) for x in raw.get("domains", [])],
                jurisdictions=[normalize_slug(str(x)) for x in raw.get("jurisdictions", [])],
                reason=str(raw.get("reason", "coverage_gap")),
            )
        )
    return batch_label, out


def parse_readiness(readiness_json: Path) -> tuple[str, list[ReadinessItem]]:
    payload = load_json(readiness_json)
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError(f"Readiness missing items: {readiness_json}")

    batch_label = str(payload.get("batch_label", "proof_batch")).strip()
    out: list[ReadinessItem] = []

    for idx, raw in enumerate(items):
        if not isinstance(raw, dict):
            raise ValueError(f"Readiness item {idx} must be object")
        out.append(
            ReadinessItem(
                kind=str(raw["kind"]),
                item_id=normalize_slug(str(raw["id"])),
                title=str(raw["title"]),
                source_dir=str(raw["source_dir"]),
                domains=[normalize_slug(str(x)) for x in raw.get("domains", [])],
                jurisdictions=[normalize_slug(str(x)) for x in raw.get("jurisdictions", [])],
                reason=str(raw.get("reason", "coverage_gap")),
                ready=bool(raw.get("ready", False)),
                readiness_score=float(raw.get("readiness_score", 0.0)),
                missing_required=[str(x) for x in raw.get("missing_required", [])],
                validation_errors=[str(x) for x in raw.get("validation_errors", [])],
                placeholder_findings=[str(x) for x in raw.get("placeholder_findings", [])],
            )
        )
    return batch_label, out


def write_operator_tasks(
    *,
    batch_label: str,
    planned_items: list[PlannedItem],
    readiness_items: list[ReadinessItem],
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir = output_dir / "operator_tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    readiness_map = {item.item_id: item for item in readiness_items}

    blocked_count = 0
    ready_count = 0
    written_files: list[str] = []

    for planned in planned_items:
        ready_state = readiness_map.get(planned.item_id)
        if ready_state is None:
            status = "missing_from_readiness"
            ready = False
            readiness_score = 0.0
            missing_required = ["not_present_in_readiness_json"]
            validation_errors = []
            placeholder_findings = []
        else:
            status = "ready" if ready_state.ready else "blocked"
            ready = ready_state.ready
            readiness_score = ready_state.readiness_score
            missing_required = ready_state.missing_required
            validation_errors = ready_state.validation_errors
            placeholder_findings = ready_state.placeholder_findings

        if ready:
            ready_count += 1
        else:
            blocked_count += 1

        md = []
        md.append(f"# Operator Task: {planned.item_id}")
        md.append("")
        md.append(f"- batch_label: `{batch_label}`")
        md.append(f"- status: `{status}`")
        md.append(f"- readiness_score: `{readiness_score}`")
        md.append(f"- kind: `{planned.kind}`")
        md.append(f"- title: `{planned.title}`")
        md.append(f"- source_dir: `{planned.source_dir}`")
        md.append(f"- domains: `{', '.join(planned.domains)}`")
        md.append(f"- jurisdictions: `{', '.join(planned.jurisdictions)}`")
        md.append(f"- reason: `{planned.reason}`")
        md.append("")
        md.append("## Required completion work")
        md.append("")
        if missing_required:
            for row in missing_required:
                md.append(f"- add required file: `{row}`")
        else:
            md.append("- no missing required files")
        if validation_errors:
            for row in validation_errors:
                md.append(f"- fix validation error: `{row}`")
        else:
            md.append("- no validation errors")
        if placeholder_findings:
            for row in placeholder_findings:
                md.append(f"- remove placeholder content: `{row}`")
        else:
            md.append("- no placeholder findings")
        md.append("")
        md.append("## Non-negotiables")
        md.append("")
        md.append("- real corpus only")
        md.append("- deterministic current audit truth only")
        md.append("- do not invent pass outcomes")
        md.append("- do not let historical context override current truth")
        md.append("- do not change taxonomy to make the item pass")
        md.append("")

        path = tasks_dir / f"{planned.item_id}.md"
        atomic_write_text(path, "\n".join(md) + "\n")
        written_files.append(str(path))

    summary = {
        "batch_label": batch_label,
        "operator_task_dir": str(tasks_dir),
        "task_file_count": len(written_files),
        "ready_count": ready_count,
        "blocked_count": blocked_count,
        "task_files": written_files,
    }
    atomic_write_json(output_dir / "operator_tasks_summary.json", summary)
    return summary


def shard_ready_items(
    ready_items: list[ReadinessItem],
    max_items_per_batch: int,
) -> list[list[ReadinessItem]]:
    if max_items_per_batch <= 0:
        raise ValueError("max_items_per_batch must be > 0")
    if not ready_items:
        return []

    ordered = sorted(
        ready_items,
        key=lambda x: (
            x.kind != "gold_case",
            x.domains[0] if x.domains else "",
            x.jurisdictions[0] if x.jurisdictions else "",
            -x.readiness_score,
            x.item_id,
        ),
    )

    shards: list[list[ReadinessItem]] = []
    for i in range(0, len(ordered), max_items_per_batch):
        shards.append(ordered[i:i + max_items_per_batch])
    return shards


def write_batch_manifests(
    *,
    batch_label: str,
    shards: list[list[ReadinessItem]],
    output_dir: Path,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for idx, shard in enumerate(shards, start=1):
        manifest_name = f"{batch_label}_shard_{idx:03d}.json"
        manifest_path = output_dir / manifest_name
        payload = {
            "items": [
                {
                    "kind": item.kind,
                    "id": item.item_id,
                    "title": item.title,
                    "source_dir": item.source_dir,
                    "domains": item.domains,
                    "jurisdictions": item.jurisdictions,
                }
                for item in shard
            ]
        }
        atomic_write_json(manifest_path, payload)
        results.append(
            {
                "shard_index": idx,
                "manifest_path": str(manifest_path),
                "item_count": len(shard),
                "item_ids": [item.item_id for item in shard],
            }
        )

    return results


def read_observed_metrics() -> dict[str, Any]:
    def maybe_load(path: Path) -> Any | None:
        return load_json(path) if path.exists() else None

    proof = maybe_load(ROOT / "logs" / "proof_density" / "proof_density_status.json")
    final_summary = maybe_load(ROOT / "logs" / "final_execution_summary.json")
    live_eval = maybe_load(ROOT / "logs" / "evals" / "live_model_eval_summary.json")
    pack_summary = maybe_load(ROOT / "logs" / "customer_pack_stability" / "summary.json")

    if isinstance(live_eval, list):
        eval_case_count = len(live_eval)
        eval_failed_count = sum(1 for row in live_eval if not row.get("passed"))
        eval_min_weighted_score = min((row.get("weighted_score", 0.0) for row in live_eval), default=0.0)
    else:
        eval_case_count = live_eval.get("case_count") if live_eval else None
        eval_failed_count = live_eval.get("failed_count") if live_eval else None
        eval_min_weighted_score = live_eval.get("min_weighted_score") if live_eval else None

    customer_pack_successful_runs = None
    if isinstance(pack_summary, dict):
        if "successful_workflow_runs" in pack_summary:
            customer_pack_successful_runs = pack_summary.get("successful_workflow_runs")
        else:
            customer_pack_successful_runs = pack_summary.get("successful_runs")

    return {
        "gold_cases_actual": proof.get("gold_cases", {}).get("gap_plan", {}).get("actual_total") if proof else None,
        "gold_cases_target": proof.get("gold_cases", {}).get("gap_plan", {}).get("target_total") if proof else None,
        "customer_packs_actual": proof.get("customer_packs", {}).get("gap_plan", {}).get("actual_total") if proof else None,
        "customer_packs_target": proof.get("customer_packs", {}).get("gap_plan", {}).get("target_total") if proof else None,
        "proof_gate_green": proof.get("gate_health", {}).get("green") if proof else None,
        "final_execution_all_steps_passed": final_summary.get("all_steps_passed") if final_summary else None,
        "eval_case_count": eval_case_count,
        "eval_failed_count": eval_failed_count,
        "eval_min_weighted_score": eval_min_weighted_score,
        "customer_pack_successful_runs": customer_pack_successful_runs,
    }


def run_validate(
    *,
    plan_json: Path,
    readiness_json: Path,
    readiness_md: Path,
    batch_manifest: Path,
    strict: bool,
    timeout_seconds: int,
) -> dict[str, Any]:
    argv = [
        sys.executable,
        str(INTAKE_MANAGER),
        "validate",
        "--plan-json",
        str(plan_json),
        "--readiness-json",
        str(readiness_json),
        "--readiness-md",
        str(readiness_md),
        "--batch-manifest",
        str(batch_manifest),
    ]
    if strict:
        argv.append("--strict")
    return run_cmd(argv, timeout_seconds)


def run_import_shard(
    *,
    manifest_path: Path,
    batch_label: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    argv = [
        sys.executable,
        str(BATCH_IMPORTER),
        "--batch-manifest",
        str(manifest_path),
        "--batch-label",
        batch_label,
    ]
    return run_cmd(argv, timeout_seconds)


def run_post_import_gates(timeout_seconds: int) -> list[dict[str, Any]]:
    steps = [
        [
            sys.executable,
            str(PROOF_DENSITY),
            "--strict",
        ],
        [
            sys.executable,
            str(FINAL_EXECUTION),
        ],
    ]
    return [run_cmd(step, timeout_seconds) for step in steps]


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Proof Execution Orchestrator Report: {report['batch_label']}")
    lines.append("")
    lines.append(f"- generated_at_epoch: `{report['generated_at_epoch']}`")
    lines.append(f"- ready_items: `{report['counts']['ready_items']}`")
    lines.append(f"- blocked_items: `{report['counts']['blocked_items']}`")
    lines.append(f"- shard_count: `{report['counts']['shard_count']}`")
    lines.append(f"- imported_shards: `{report['counts']['imported_shards']}`")
    lines.append(f"- failed_shards: `{report['counts']['failed_shards']}`")
    lines.append("")
    lines.append("## Observed Metrics")
    lines.append("")
    for k, v in report["observed_metrics"].items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    lines.append("## Shards")
    lines.append("")
    for shard in report["shards"]:
        lines.append(f"### shard_{shard['shard_index']:03d}")
        lines.append(f"- item_count: `{shard['item_count']}`")
        lines.append(f"- item_ids: `{shard['item_ids']}`")
        lines.append(f"- manifest_path: `{shard['manifest_path']}`")
        lines.append(f"- imported: `{shard.get('imported')}`")
        if "import_result" in shard:
            lines.append(f"- import_passed: `{shard['import_result']['passed']}`")
            lines.append(f"- import_returncode: `{shard['import_result']['returncode']}`")
        if "post_import_gates" in shard:
            for idx, gate in enumerate(shard["post_import_gates"], start=1):
                lines.append(f"- gate_{idx}_passed: `{gate['passed']}`")
        lines.append("")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="End-to-end proof execution orchestrator")
    parser.add_argument("--plan-json", default=str(DEFAULT_PLAN_JSON))
    parser.add_argument("--readiness-json", default=str(DEFAULT_READINESS_JSON))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--batch-manifest-dir", default=str(DEFAULT_BATCH_MANIFEST_DIR))
    parser.add_argument("--max-items-per-batch", type=int, default=5)
    parser.add_argument("--validate-first", action="store_true")
    parser.add_argument("--strict-validate", action="store_true")
    parser.add_argument("--write-operator-tasks", action="store_true")
    parser.add_argument("--execute-imports", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=2400)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    plan_json = Path(args.plan_json)
    readiness_json = Path(args.readiness_json)
    output_dir = Path(args.output_dir)
    batch_manifest_dir = Path(args.batch_manifest_dir)
    readiness_md = output_dir / "refreshed_readiness.md"
    ready_only_manifest = output_dir / "ready_only_manifest.json"

    batch_label, planned_items = parse_plan(plan_json)

    validation_step = None
    if args.validate_first:
        validation_step = run_validate(
            plan_json=plan_json,
            readiness_json=readiness_json,
            readiness_md=readiness_md,
            batch_manifest=ready_only_manifest,
            strict=args.strict_validate,
            timeout_seconds=args.timeout_seconds,
        )
        if not validation_step["passed"] and args.strict_validate:
            report = {
                "generated_at_epoch": int(time.time()),
                "batch_label": batch_label,
                "validation_step": validation_step,
                "counts": {
                    "ready_items": 0,
                    "blocked_items": 0,
                    "shard_count": 0,
                    "imported_shards": 0,
                    "failed_shards": 1,
                },
                "shards": [],
                "observed_metrics": read_observed_metrics(),
            }
            output_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_json(output_dir / "orchestrator_report.json", report)
            atomic_write_text(output_dir / "orchestrator_report.md", render_markdown(report))
            print(json.dumps(report, indent=2))
            return 1

    readiness_batch_label, readiness_items = parse_readiness(readiness_json)
    if readiness_batch_label and readiness_batch_label != batch_label:
        raise ValueError(f"Batch label mismatch plan={batch_label} readiness={readiness_batch_label}")

    ready_items = [x for x in readiness_items if x.ready]
    blocked_items = [x for x in readiness_items if not x.ready]

    operator_tasks_summary = None
    if args.write_operator_tasks:
        operator_tasks_summary = write_operator_tasks(
            batch_label=batch_label,
            planned_items=planned_items,
            readiness_items=readiness_items,
            output_dir=output_dir,
        )

    shards = shard_ready_items(ready_items, args.max_items_per_batch)
    shard_manifests = write_batch_manifests(
        batch_label=batch_label,
        shards=shards,
        output_dir=batch_manifest_dir,
    )

    imported_shards = 0
    failed_shards = 0
    enriched_shards: list[dict[str, Any]] = []

    for shard in shard_manifests:
        enriched = dict(shard)
        enriched["imported"] = False

        if args.execute_imports:
            import_result = run_import_shard(
                manifest_path=Path(shard["manifest_path"]),
                batch_label=f"{batch_label}_shard_{shard['shard_index']:03d}",
                timeout_seconds=args.timeout_seconds,
            )
            enriched["import_result"] = import_result
            enriched["imported"] = True

            if import_result["passed"]:
                gates = run_post_import_gates(timeout_seconds=args.timeout_seconds)
                enriched["post_import_gates"] = gates
                if all(step["passed"] for step in gates):
                    imported_shards += 1
                else:
                    failed_shards += 1
                    enriched_shards.append(enriched)
                    break
            else:
                failed_shards += 1
                enriched_shards.append(enriched)
                break

        enriched_shards.append(enriched)

    observed_metrics = read_observed_metrics()

    report = {
        "generated_at_epoch": int(time.time()),
        "batch_label": batch_label,
        "validation_step": validation_step,
        "operator_tasks_summary": operator_tasks_summary,
        "counts": {
            "ready_items": len(ready_items),
            "blocked_items": len(blocked_items),
            "shard_count": len(shard_manifests),
            "imported_shards": imported_shards,
            "failed_shards": failed_shards,
        },
        "shards": enriched_shards,
        "observed_metrics": observed_metrics,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(output_dir / "orchestrator_report.json", report)
    atomic_write_text(output_dir / "orchestrator_report.md", render_markdown(report))

    print(json.dumps({
        "batch_label": batch_label,
        "ready_items": len(ready_items),
        "blocked_items": len(blocked_items),
        "shard_count": len(shard_manifests),
        "imported_shards": imported_shards,
        "failed_shards": failed_shards,
        "report_json": str(output_dir / "orchestrator_report.json"),
        "report_md": str(output_dir / "orchestrator_report.md"),
        "observed_metrics": observed_metrics,
    }, indent=2))

    if failed_shards > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
