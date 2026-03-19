from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


ROOT = Path.cwd()
DEFAULT_CONFIG_PATH = ROOT / "config" / "proof_expansion_config.json"
PIPELINE_PATH = ROOT / "scripts" / "proof_expansion_pipeline.py"


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


def read_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing config: {path}")
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Config must be a JSON object: {path}")
    return payload


def assert_relative_path(value: str) -> None:
    p = Path(value)
    if p.is_absolute():
        raise ValueError(f"Path must be relative to repo root: {value}")
    if ".." in p.parts:
        raise ValueError(f"Parent traversal not allowed: {value}")


@dataclass(frozen=True)
class BatchItem:
    kind: str
    item_id: str
    source_dir: str
    title: str | None
    domains: list[str] | None
    jurisdictions: list[str] | None


def parse_batch_manifest(path: Path) -> list[BatchItem]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("Batch manifest must be a JSON object")
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("Batch manifest must contain a non-empty items array")

    out: list[BatchItem] = []
    seen_ids: set[tuple[str, str]] = set()

    for idx, raw in enumerate(items):
        if not isinstance(raw, dict):
            raise ValueError(f"Item {idx} must be an object")
        kind = str(raw.get("kind", "")).strip()
        item_id = normalize_slug(str(raw.get("id", "")).strip())
        source_dir = str(raw.get("source_dir", "")).strip()
        title = raw.get("title")
        domains = raw.get("domains")
        jurisdictions = raw.get("jurisdictions")

        if kind not in {"gold_case", "customer_pack"}:
            raise ValueError(f"Item {idx} has invalid kind: {kind}")
        if not item_id:
            raise ValueError(f"Item {idx} missing id")
        if not source_dir:
            raise ValueError(f"Item {idx} missing source_dir")

        assert_relative_path(source_dir)

        key = (kind, item_id)
        if key in seen_ids:
            raise ValueError(f"Duplicate item in batch: {kind}:{item_id}")
        seen_ids.add(key)

        if domains is not None:
            if not isinstance(domains, list) or not domains:
                raise ValueError(f"Item {idx} domains must be a non-empty list when supplied")
            domains = [normalize_slug(str(x)) for x in domains]

        if jurisdictions is not None:
            if not isinstance(jurisdictions, list) or not jurisdictions:
                raise ValueError(f"Item {idx} jurisdictions must be a non-empty list when supplied")
            jurisdictions = [normalize_slug(str(x)) for x in jurisdictions]

        out.append(
            BatchItem(
                kind=kind,
                item_id=item_id,
                source_dir=source_dir,
                title=str(title) if title is not None else None,
                domains=domains,
                jurisdictions=jurisdictions,
            )
        )

    return out


def run_cmd(argv: list[str], timeout_seconds: int) -> dict[str, Any]:
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


def get_target_dir(config: dict[str, Any], kind: str, item_id: str) -> Path:
    if kind == "gold_case":
        return ROOT / config["paths"]["gold_cases_root"] / item_id
    if kind == "customer_pack":
        return ROOT / config["paths"]["customer_packs_root"] / item_id
    raise ValueError(f"Unsupported kind: {kind}")


def build_pipeline_argv(
    *,
    config_path: Path,
    item: BatchItem,
    dry_run: bool,
    skip_gates: bool,
) -> list[str]:
    argv = [
        sys.executable,
        str(PIPELINE_PATH),
        "--config",
        str(config_path),
        "--kind",
        item.kind,
        "--id",
        item.item_id,
        "--source-dir",
        item.source_dir,
    ]
    if item.title:
        argv.extend(["--title", item.title])
    if item.domains:
        argv.extend(["--domains", ",".join(item.domains)])
    if item.jurisdictions:
        argv.extend(["--jurisdictions", ",".join(item.jurisdictions)])
    if dry_run:
        argv.append("--dry-run")
    if skip_gates:
        argv.append("--skip-gates")
    return argv


def validate_batch(
    *,
    config_path: Path,
    items: list[BatchItem],
    timeout_seconds: int,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in items:
        argv = build_pipeline_argv(
            config_path=config_path,
            item=item,
            dry_run=True,
            skip_gates=True,
        )
        result = run_cmd(argv, timeout_seconds)
        results.append(
            {
                "kind": item.kind,
                "id": item.item_id,
                "source_dir": item.source_dir,
                **result,
            }
        )
    return results


def import_batch(
    *,
    config_path: Path,
    config: dict[str, Any],
    items: list[BatchItem],
    timeout_seconds: int,
) -> tuple[list[dict[str, Any]], list[Path]]:
    results: list[dict[str, Any]] = []
    created_paths: list[Path] = []

    for item in items:
        argv = build_pipeline_argv(
            config_path=config_path,
            item=item,
            dry_run=False,
            skip_gates=True,
        )
        result = run_cmd(argv, timeout_seconds)
        results.append(
            {
                "kind": item.kind,
                "id": item.item_id,
                "source_dir": item.source_dir,
                **result,
            }
        )
        if not result["passed"]:
            break

        created_paths.append(get_target_dir(config, item.kind, item.item_id))

    return results, created_paths


def rollback_paths(paths: list[Path]) -> list[str]:
    removed: list[str] = []
    for path in reversed(paths):
        if path.exists():
            shutil.rmtree(path)
            removed.append(str(path))
    return removed


def run_post_import_gates(config: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for gate in config.get("gate_commands", []):
        if not gate.get("enabled", True):
            continue
        argv = [sys.executable, *gate["argv"]]
        step = run_cmd(argv, int(gate["timeout_seconds"]))
        step["name"] = gate["name"]
        results.append(step)
    return results


def summarize_counts(config: dict[str, Any]) -> dict[str, int]:
    gold_root = ROOT / config["paths"]["gold_cases_root"]
    pack_root = ROOT / config["paths"]["customer_packs_root"]

    def count_leaf_dirs(root: Path, exclude: set[str] | None = None) -> int:
        if not root.exists():
            return 0
        excluded = exclude or set()
        return sum(1 for p in root.iterdir() if p.is_dir() and p.name not in excluded)

    return {
        "gold_cases_count": count_leaf_dirs(gold_root),
        "customer_packs_count": count_leaf_dirs(pack_root, {"_template"}),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transactional Tenet proof batch importer")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--batch-manifest", required=True)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--batch-label", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    config = read_config(config_path)

    assert_relative_path(args.batch_manifest)
    batch_manifest_path = ROOT / args.batch_manifest
    items = parse_batch_manifest(batch_manifest_path)

    batch_label = args.batch_label or f"batch_{int(time.time())}"
    batch_log_dir = ROOT / config["paths"]["batch_output_root"] / batch_label
    batch_log_dir.mkdir(parents=True, exist_ok=True)

    pre_counts = summarize_counts(config)

    validation_results = validate_batch(
        config_path=config_path,
        items=items,
        timeout_seconds=args.timeout_seconds,
    )

    validation_failed = [r for r in validation_results if not r["passed"]]
    preflight = {
        "batch_label": batch_label,
        "validate_only": args.validate_only,
        "item_count": len(items),
        "pre_counts": pre_counts,
        "validation_results": validation_results,
        "validation_green": len(validation_failed) == 0,
    }
    atomic_write_json(batch_log_dir / "preflight.json", preflight)

    if validation_failed or args.validate_only:
        print(json.dumps(preflight, indent=2))
        return 1 if validation_failed else 0

    import_results, created_paths = import_batch(
        config_path=config_path,
        config=config,
        items=items,
        timeout_seconds=args.timeout_seconds,
    )

    import_failed = [r for r in import_results if not r["passed"]]
    rollback_performed = False
    rollback_removed_paths: list[str] = []
    gate_results: list[dict[str, Any]] = []

    if import_failed:
        rollback_removed_paths = rollback_paths(created_paths)
        rollback_performed = True
    else:
        gate_results = run_post_import_gates(config)
        gate_failed = [r for r in gate_results if not r["passed"]]
        if gate_failed:
            rollback_removed_paths = rollback_paths(created_paths)
            rollback_performed = True

    post_counts = summarize_counts(config)

    outcome = {
        "batch_label": batch_label,
        "item_count": len(items),
        "pre_counts": pre_counts,
        "post_counts": post_counts,
        "import_results": import_results,
        "gate_results": gate_results,
        "rollback_performed": rollback_performed,
        "rollback_removed_paths": rollback_removed_paths,
        "success": (not import_failed) and (not rollback_performed),
    }

    atomic_write_json(batch_log_dir / "outcome.json", outcome)
    print(json.dumps(outcome, indent=2))
    return 0 if outcome["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
