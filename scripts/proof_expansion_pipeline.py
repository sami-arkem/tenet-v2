from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.loader import load_eval_cases
from src.core.io_utils import atomic_write_json
from src.workflow.evidence_pack_loader import load_evidence_pack

DEFAULT_CONFIG_PATH = ROOT / "config" / "proof_expansion_config.json"


def normalize_slug(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("&", "and")
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing config: {path}")
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Config must be a JSON object: {path}")
    return payload


def _taxonomy_values(config: dict[str, Any], key: str) -> list[str]:
    direct = config.get(f"allowed_{key}")
    if isinstance(direct, list):
        return [normalize_slug(str(x)) for x in direct if str(x).strip()]
    nested = (config.get("taxonomy") or {}).get(key)
    if isinstance(nested, list):
        return [normalize_slug(str(x)) for x in nested if str(x).strip()]
    raise ValueError(f"Missing taxonomy values for {key}")


def assert_relative_path(value: str) -> None:
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"Path must be relative to repo root: {value}")
    if ".." in path.parts:
        raise ValueError(f"Parent traversal not allowed: {value}")


def normalize_list(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    values = [normalize_slug(part) for part in raw.split(",") if part.strip()]
    return values or None


def ensure_allowed(values: list[str] | None, allowed: set[str], label: str) -> None:
    if not values:
        return
    invalid = sorted(value for value in values if value not in allowed)
    if invalid:
        raise ValueError(f"Unsupported {label}: {invalid}")


def ensure_clean_target(target_dir: Path) -> None:
    if target_dir.exists():
        raise FileExistsError(f"Target already exists: {target_dir}")


def _validate_common_source_dir(source_dir: Path) -> None:
    if not source_dir.exists() or not source_dir.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")


def _validate_gold_case_contract(
    source_dir: Path,
    expected_id: str,
    expected_domains: list[str] | None,
    expected_jurisdictions: list[str] | None,
    allowed_domains: set[str],
    allowed_jurisdictions: set[str],
) -> dict[str, Any]:
    _validate_common_source_dir(source_dir)

    audit_context = load_json(source_dir / "audit_context.json")
    expected_assertions = load_json(source_dir / "expected_assertions.json")
    case_notes = (source_dir / "case_notes.md").read_text(encoding="utf-8")

    if not isinstance(audit_context, dict):
        raise ValueError(f"audit_context.json must be an object: {source_dir}")
    if not isinstance(expected_assertions, dict):
        raise ValueError(f"expected_assertions.json must be an object: {source_dir}")
    if not case_notes.strip():
        raise ValueError(f"case_notes.md must not be empty: {source_dir}")

    required_audit_fields = {
        "audit_id",
        "entity_name",
        "audit_type",
        "industry",
        "jurisdictions",
        "source_families",
        "query_terms",
        "top_k",
    }
    missing = sorted(required_audit_fields - set(audit_context.keys()))
    if missing:
        raise ValueError(f"Gold case missing audit_context fields: {missing}")

    case_id = str(expected_assertions.get("case_id") or source_dir.name)
    if normalize_slug(case_id) != expected_id:
        raise ValueError(f"Gold case expected_assertions.case_id mismatch: {case_id} != {expected_id}")

    domains = [normalize_slug(x) for x in (audit_context.get("domains") or []) if str(x).strip()]
    jurisdictions = [normalize_slug(x) for x in (audit_context.get("jurisdictions") or []) if str(x).strip()]

    ensure_allowed(domains, allowed_domains, "domains")
    ensure_allowed(jurisdictions, allowed_jurisdictions, "jurisdictions")

    if expected_domains is not None and sorted(expected_domains) != sorted(domains):
        raise ValueError(f"Gold case domains mismatch: {domains} != {expected_domains}")
    if expected_jurisdictions is not None and sorted(expected_jurisdictions) != sorted(jurisdictions):
        raise ValueError(f"Gold case jurisdictions mismatch: {jurisdictions} != {expected_jurisdictions}")

    # Validate against the real eval loader contract on an isolated staging root.
    with tempfile.TemporaryDirectory() as tmp_dir:
        staging_root = Path(tmp_dir)
        staging_case_dir = staging_root / source_dir.name
        shutil.copytree(source_dir, staging_case_dir)
        cases = load_eval_cases(staging_root)
        if len(cases) != 1:
            raise ValueError(f"Gold case contract did not load as exactly one eval case: {source_dir}")

    return {
        "domains": domains,
        "jurisdictions": jurisdictions,
        "title": audit_context.get("entity_name"),
    }


def _validate_customer_pack_contract(
    source_dir: Path,
    expected_id: str,
    expected_domains: list[str] | None,
    expected_jurisdictions: list[str] | None,
    allowed_domains: set[str],
    allowed_jurisdictions: set[str],
) -> dict[str, Any]:
    _validate_common_source_dir(source_dir)
    pack = load_evidence_pack(source_dir)
    audit_context = pack["audit_context"]

    actual_id = normalize_slug(str(audit_context.get("audit_id", "") or source_dir.name))
    if actual_id != expected_id:
        raise ValueError(f"Customer pack audit_id mismatch: {actual_id} != {expected_id}")

    domains = [normalize_slug(x) for x in (audit_context.get("domains") or []) if str(x).strip()]
    jurisdictions = [normalize_slug(x) for x in (audit_context.get("jurisdictions") or []) if str(x).strip()]

    ensure_allowed(domains, allowed_domains, "domains")
    ensure_allowed(jurisdictions, allowed_jurisdictions, "jurisdictions")

    if expected_domains is not None and sorted(expected_domains) != sorted(domains):
        raise ValueError(f"Customer pack domains mismatch: {domains} != {expected_domains}")
    if expected_jurisdictions is not None and sorted(expected_jurisdictions) != sorted(jurisdictions):
        raise ValueError(f"Customer pack jurisdictions mismatch: {jurisdictions} != {expected_jurisdictions}")

    return {
        "domains": domains,
        "jurisdictions": jurisdictions,
        "title": audit_context.get("entity_name"),
    }


def validate_item(
    *,
    kind: str,
    source_dir: Path,
    item_id: str,
    expected_domains: list[str] | None,
    expected_jurisdictions: list[str] | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    allowed_domains = set(_taxonomy_values(config, "domains"))
    allowed_jurisdictions = set(_taxonomy_values(config, "jurisdictions"))

    if kind == "gold_case":
        return _validate_gold_case_contract(
            source_dir,
            item_id,
            expected_domains,
            expected_jurisdictions,
            allowed_domains,
            allowed_jurisdictions,
        )
    if kind == "customer_pack":
        return _validate_customer_pack_contract(
            source_dir,
            item_id,
            expected_domains,
            expected_jurisdictions,
            allowed_domains,
            allowed_jurisdictions,
        )
    raise ValueError(f"Unsupported kind: {kind}")


def target_dir_for(config: dict[str, Any], kind: str, item_id: str) -> Path:
    if kind == "gold_case":
        return ROOT / config["paths"]["gold_cases_root"] / item_id
    if kind == "customer_pack":
        return ROOT / config["paths"]["customer_packs_root"] / item_id
    raise ValueError(f"Unsupported kind: {kind}")


def load_plan_recommendations(kind: str, limit: int) -> dict[str, Any]:
    proof_density_path = ROOT / "logs" / "proof_density" / "proof_density_status.json"
    if not proof_density_path.exists():
        raise FileNotFoundError(f"Missing proof density status: {proof_density_path}")
    payload = load_json(proof_density_path)
    section_key = "gold_cases" if kind == "gold_case" else "customer_packs"
    gap_plan = ((payload or {}).get(section_key) or {}).get("gap_plan") or {}
    recommendations = list(gap_plan.get("recommended_next_batch", []) or [])[:limit]
    return {
        "kind": kind,
        "recommend_limit": limit,
        "actual_total": gap_plan.get("actual_total"),
        "target_total": gap_plan.get("target_total"),
        "remaining_to_target": gap_plan.get("remaining_to_target"),
        "recommended_next_batch": recommendations,
    }


def atomic_copytree(source_dir: Path, target_dir: Path) -> None:
    ensure_clean_target(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = target_dir.parent / f".{target_dir.name}.tmp.{int(time.time() * 1000)}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    shutil.copytree(source_dir, tmp_dir)
    tmp_dir.replace(target_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Strict single-item proof expansion pipeline")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--kind", required=True, choices=["gold_case", "customer_pack"])
    parser.add_argument("--id", required=True)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--title", default=None)
    parser.add_argument("--domains", default=None)
    parser.add_argument("--jurisdictions", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-gates", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--recommend-limit", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = read_config(Path(args.config))

    item_id = normalize_slug(args.id)
    if args.plan_only:
        plan = load_plan_recommendations(args.kind, args.recommend_limit)
        print(json.dumps(plan, indent=2))
        return 0

    assert_relative_path(args.source_dir)
    source_dir = ROOT / args.source_dir
    target_dir = target_dir_for(config, args.kind, item_id)

    validation = validate_item(
        kind=args.kind,
        source_dir=source_dir,
        item_id=item_id,
        expected_domains=normalize_list(args.domains),
        expected_jurisdictions=normalize_list(args.jurisdictions),
        config=config,
    )
    ensure_clean_target(target_dir)

    result = {
        "kind": args.kind,
        "id": item_id,
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "dry_run": args.dry_run,
        "validation": validation,
        "skip_gates": args.skip_gates,
        "committed": False,
    }

    if not args.dry_run:
        atomic_copytree(source_dir, target_dir)
        result["committed"] = True

    log_dir = ROOT / config["paths"]["batch_output_root"] / "single_item_runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(log_dir / f"{args.kind}__{item_id}.json", result)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
