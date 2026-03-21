from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from src.core.io_utils import atomic_write_json


AUDIT_MEMORY_ROOT = Path("data/memory/snapshots")
REMEDIATION_COMPARISON_ROOT = Path("data/memory/remediation_comparisons")
TREND_ROOT = Path("data/memory/trends")

DECISION_RANK = {
    "BLOCKED": 0,
    "CONDITIONALLY_APPROVED": 1,
    "APPROVED": 2,
}

THEME_DOMAIN_ALIASES = {
    "governance": {"governance"},
    "screening": {"screening", "transaction_screening", "sanctions"},
    "licensing": {"regulatory_licensing", "vendor_risk"},
    "remediation": {"remediation_tracking"},
}

CONTROL_THEME_MAP = {
    "GOV-001": {"governance"},
    "SAN-001": {"screening"},
    "VEN-001": {"licensing"},
}


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _dedupe_keep_order(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _entity_slug(entity_name: str) -> str:
    return entity_name.lower().replace(" ", "_").replace("/", "_")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sorted_snapshots(paths: List[Path]) -> List[Dict[str, Any]]:
    snapshots = [_read_json(p) for p in paths]
    return sorted(
        snapshots,
        key=lambda x: (
            _safe_str(x.get("written_at_utc", "")),
            _safe_str(x.get("audit_id", "")),
        ),
    )


def load_entity_audit_snapshots(entity_name: str) -> List[Dict[str, Any]]:
    entity_dir = AUDIT_MEMORY_ROOT / _entity_slug(entity_name)
    if not entity_dir.exists():
        return []
    return _sorted_snapshots(sorted(entity_dir.glob("*.json")))


def load_entity_remediation_comparisons(entity_name: str) -> List[Dict[str, Any]]:
    entity_dir = REMEDIATION_COMPARISON_ROOT / _entity_slug(entity_name)
    if not entity_dir.exists():
        return []
    comparisons = [_read_json(p) for p in sorted(entity_dir.glob("*.json"))]
    return sorted(
        comparisons,
        key=lambda x: (
            _safe_str(x.get("compared_at_utc", "")),
            _safe_str(x.get("prior_audit_id", "")),
            _safe_str(x.get("current_audit_id", "")),
        ),
    )


def _decision_trajectory(audit_snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
    decisions = [
        {
            "audit_id": _safe_str(s.get("audit_id", "")),
            "decision": _safe_str((s.get("deployment_decision", {}) or {}).get("status", "")),
            "written_at_utc": _safe_str(s.get("written_at_utc", "")),
        }
        for s in audit_snapshots
    ]
    decisions = [d for d in decisions if d["decision"]]

    if len(decisions) < 2:
        return {
            "status": "insufficient_history",
            "first_decision": decisions[0]["decision"] if decisions else "",
            "latest_decision": decisions[-1]["decision"] if decisions else "",
            "history": decisions,
        }

    first_rank = DECISION_RANK.get(decisions[0]["decision"], 0)
    last_rank = DECISION_RANK.get(decisions[-1]["decision"], 0)

    if last_rank > first_rank:
        status = "improving"
    elif last_rank < first_rank:
        status = "worsening"
    else:
        status = "stable"

    return {
        "status": status,
        "first_decision": decisions[0]["decision"],
        "latest_decision": decisions[-1]["decision"],
        "history": decisions,
    }


def _ranked_counter(counter: Counter) -> List[Dict[str, Any]]:
    return [
        {"key": key, "count": count}
        for key, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


def _ranked_control_counter(counter: Counter) -> List[Dict[str, Any]]:
    return [
        {"control_id": key, "count": count}
        for key, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


def _theme_controls_for_snapshot(snapshot: Dict[str, Any], control_id: str) -> List[str]:
    explicit_themes = CONTROL_THEME_MAP.get(control_id, set())
    if explicit_themes:
        return sorted(explicit_themes)

    themes = set()
    domains = set(snapshot.get("domains", []) or [])
    for theme, aliases in THEME_DOMAIN_ALIASES.items():
        if domains & aliases:
            themes.add(theme)
    return sorted(themes)


def _theme_summary(audit_snapshots: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    theme_counters: Dict[str, Counter] = defaultdict(Counter)

    for snapshot in audit_snapshots:
        missing_controls = snapshot.get("missing_controls_control_ids", []) or []
        for control_id in missing_controls:
            for theme in _theme_controls_for_snapshot(snapshot, control_id):
                theme_counters[theme][control_id] += 1

    result: Dict[str, List[Dict[str, Any]]] = {}
    for theme in ["governance", "screening", "licensing", "remediation"]:
        recurring_only = {k: v for k, v in theme_counters.get(theme, Counter()).items() if v >= 2}
        result[f"repeated_{theme}_weaknesses"] = _ranked_control_counter(Counter(recurring_only))
    return result


def _remediation_trajectory(remediation_comparisons: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not remediation_comparisons:
        return {
            "status": "insufficient_history",
            "comparison_count": 0,
            "newly_closed_total": 0,
            "newly_open_total": 0,
            "still_open_total": 0,
            "improved_total": 0,
        }

    newly_closed_total = sum(len(x.get("newly_closed_controls", []) or []) for x in remediation_comparisons)
    newly_open_total = sum(len(x.get("newly_open_controls", []) or []) for x in remediation_comparisons)
    still_open_total = sum(len(x.get("still_open_controls", []) or []) for x in remediation_comparisons)
    improved_total = sum(len(x.get("improved_controls", []) or []) for x in remediation_comparisons)

    if improved_total > newly_open_total:
        status = "improving"
    elif improved_total < newly_open_total:
        status = "worsening"
    else:
        status = "stable"

    return {
        "status": status,
        "comparison_count": len(remediation_comparisons),
        "newly_closed_total": newly_closed_total,
        "newly_open_total": newly_open_total,
        "still_open_total": still_open_total,
        "improved_total": improved_total,
    }


def build_entity_trend_summary(
    audit_snapshots: List[Dict[str, Any]],
    remediation_comparisons: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not audit_snapshots:
        raise ValueError("audit_snapshots must not be empty")

    ordered = sorted(
        audit_snapshots,
        key=lambda x: (
            _safe_str(x.get("written_at_utc", "")),
            _safe_str(x.get("audit_id", "")),
        ),
    )

    entity_name = _safe_str(ordered[-1].get("entity_name", "")) or "Unknown Entity"
    audit_ids = [_safe_str(x.get("audit_id", "")) for x in ordered]
    jurisdictions = _dedupe_keep_order(
        item
        for snapshot in ordered
        for item in (snapshot.get("jurisdictions", []) or [])
    )
    domains = _dedupe_keep_order(
        item
        for snapshot in ordered
        for item in (snapshot.get("domains", []) or [])
    )

    missing_controls_counter = Counter(
        control_id
        for snapshot in ordered
        for control_id in (snapshot.get("missing_controls_control_ids", []) or [])
        if control_id
    )
    findings_counter = Counter(
        control_id
        for snapshot in ordered
        for control_id in (snapshot.get("findings_control_ids", []) or [])
        if control_id
    )

    recurring_missing_controls = [
        row for row in _ranked_control_counter(missing_controls_counter) if row["count"] >= 2
    ]
    recurring_findings = [
        row for row in _ranked_control_counter(findings_counter) if row["count"] >= 2
    ]

    theme_summary = _theme_summary(ordered)
    decision_trajectory = _decision_trajectory(ordered)
    remediation_trajectory = _remediation_trajectory(remediation_comparisons)

    return {
        "trend_version": "v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "entity_name": entity_name,
        "audit_count": len(ordered),
        "audit_ids": audit_ids,
        "jurisdictions": jurisdictions,
        "domains": domains,
        "decision_trajectory": decision_trajectory,
        "recurring_missing_controls": recurring_missing_controls,
        "recurring_findings": recurring_findings,
        **theme_summary,
        "remediation_improvement_trajectory": remediation_trajectory,
    }


def write_entity_trend_summary(entity_name: str) -> Path | None:
    audit_snapshots = load_entity_audit_snapshots(entity_name)
    if not audit_snapshots:
        return None

    remediation_comparisons = load_entity_remediation_comparisons(entity_name)
    summary = build_entity_trend_summary(audit_snapshots, remediation_comparisons)

    out_dir = TREND_ROOT
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{_entity_slug(entity_name)}.json"
    atomic_write_json(out_path, summary)
    return out_path


def write_all_entity_trend_summaries() -> List[Path]:
    if not AUDIT_MEMORY_ROOT.exists():
        return []

    written: List[Path] = []
    for entity_dir in sorted(p for p in AUDIT_MEMORY_ROOT.iterdir() if p.is_dir()):
        entity_name = entity_dir.name.replace("_", " ")
        out = write_entity_trend_summary(entity_name)
        if out is not None:
            written.append(out)
    return written
