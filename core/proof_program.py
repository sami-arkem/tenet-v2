from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


DEFAULT_MANIFEST_VERSION = "1.0"
DEFAULT_GOLD_TARGET = 100
DEFAULT_CUSTOMER_PACK_TARGET = 20
DEFAULT_STATE_PATH = Path("state") / "proof_program" / "manifest.json"
DEFAULT_SUMMARY_JSON_PATH = Path("state") / "proof_program" / "readiness_summary.json"
DEFAULT_SUMMARY_MD_PATH = Path("state") / "proof_program" / "readiness_summary.md"


def _utc_epoch() -> int:
    return int(time.time())


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _sorted_unique(values: list[str]) -> list[str]:
    cleaned = [_require_non_empty_str(value, "list item") for value in values if isinstance(value, str) and value.strip()]
    return sorted(set(cleaned))


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class GoldCaseRecord:
    case_id: str
    title: str
    domain: str
    jurisdiction: str
    framework: str
    control_id: str
    status: str
    created_at_epoch: int
    updated_at_epoch: int
    notes: str | None = None

    @staticmethod
    def normalize_status(status: str) -> str:
        normalized = _require_non_empty_str(status, "status").upper()
        allowed = {"PASS", "FAIL", "BLOCKED"}
        if normalized not in allowed:
            raise ValueError(f"unsupported gold case status: {status}")
        return normalized

    @classmethod
    def create(
        cls,
        *,
        case_id: str,
        title: str,
        domain: str,
        jurisdiction: str,
        framework: str,
        control_id: str,
        status: str,
        notes: str | None = None,
        now_epoch: int | None = None,
    ) -> "GoldCaseRecord":
        now = now_epoch or _utc_epoch()
        return cls(
            case_id=_require_non_empty_str(case_id, "case_id"),
            title=_require_non_empty_str(title, "title"),
            domain=_require_non_empty_str(domain, "domain"),
            jurisdiction=_require_non_empty_str(jurisdiction, "jurisdiction"),
            framework=_require_non_empty_str(framework, "framework"),
            control_id=_require_non_empty_str(control_id, "control_id"),
            status=cls.normalize_status(status),
            created_at_epoch=now,
            updated_at_epoch=now,
            notes=_require_non_empty_str(notes, "notes") if isinstance(notes, str) and notes.strip() else None,
        )


@dataclass(frozen=True)
class CustomerPackRecord:
    pack_id: str
    customer_name: str
    domain: str
    jurisdiction: str
    framework: str
    status: str
    created_at_epoch: int
    updated_at_epoch: int
    notes: str | None = None

    @staticmethod
    def normalize_status(status: str) -> str:
        normalized = _require_non_empty_str(status, "status").upper()
        allowed = {"ACTIVE", "STABLE", "FAILED", "BLOCKED"}
        if normalized not in allowed:
            raise ValueError(f"unsupported customer pack status: {status}")
        return normalized

    @classmethod
    def create(
        cls,
        *,
        pack_id: str,
        customer_name: str,
        domain: str,
        jurisdiction: str,
        framework: str,
        status: str,
        notes: str | None = None,
        now_epoch: int | None = None,
    ) -> "CustomerPackRecord":
        now = now_epoch or _utc_epoch()
        return cls(
            pack_id=_require_non_empty_str(pack_id, "pack_id"),
            customer_name=_require_non_empty_str(customer_name, "customer_name"),
            domain=_require_non_empty_str(domain, "domain"),
            jurisdiction=_require_non_empty_str(jurisdiction, "jurisdiction"),
            framework=_require_non_empty_str(framework, "framework"),
            status=cls.normalize_status(status),
            created_at_epoch=now,
            updated_at_epoch=now,
            notes=_require_non_empty_str(notes, "notes") if isinstance(notes, str) and notes.strip() else None,
        )


@dataclass(frozen=True)
class FinalExecutionDiscipline:
    suite_green: bool
    last_run_epoch: int | None
    last_run_ref: str | None
    failing_gate_names: list[str] = field(default_factory=list)

    @classmethod
    def healthy(cls, *, ref: str | None = None, now_epoch: int | None = None) -> "FinalExecutionDiscipline":
        return cls(
            suite_green=True,
            last_run_epoch=now_epoch or _utc_epoch(),
            last_run_ref=_require_non_empty_str(ref, "ref") if isinstance(ref, str) and ref.strip() else None,
            failing_gate_names=[],
        )

    @classmethod
    def unhealthy(
        cls,
        *,
        failing_gate_names: list[str],
        ref: str | None = None,
        now_epoch: int | None = None,
    ) -> "FinalExecutionDiscipline":
        gates = _sorted_unique(failing_gate_names)
        if not gates:
            raise ValueError("failing_gate_names must be non-empty when discipline is unhealthy")
        return cls(
            suite_green=False,
            last_run_epoch=now_epoch or _utc_epoch(),
            last_run_ref=_require_non_empty_str(ref, "ref") if isinstance(ref, str) and ref.strip() else None,
            failing_gate_names=gates,
        )


@dataclass(frozen=True)
class ProofProgramManifest:
    version: str
    gold_target: int
    customer_pack_target: int
    gold_cases: list[GoldCaseRecord]
    customer_packs: list[CustomerPackRecord]
    final_execution: FinalExecutionDiscipline

    @classmethod
    def empty(
        cls,
        *,
        gold_target: int = DEFAULT_GOLD_TARGET,
        customer_pack_target: int = DEFAULT_CUSTOMER_PACK_TARGET,
    ) -> "ProofProgramManifest":
        return cls(
            version=DEFAULT_MANIFEST_VERSION,
            gold_target=gold_target,
            customer_pack_target=customer_pack_target,
            gold_cases=[],
            customer_packs=[],
            final_execution=FinalExecutionDiscipline.unhealthy(
                failing_gate_names=["final_execution_not_recorded"],
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "gold_target": self.gold_target,
            "customer_pack_target": self.customer_pack_target,
            "gold_cases": [asdict(item) for item in self.gold_cases],
            "customer_packs": [asdict(item) for item in self.customer_packs],
            "final_execution": asdict(self.final_execution),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProofProgramManifest":
        return cls(
            version=_require_non_empty_str(payload["version"], "version"),
            gold_target=int(payload["gold_target"]),
            customer_pack_target=int(payload["customer_pack_target"]),
            gold_cases=[GoldCaseRecord(**item) for item in payload.get("gold_cases", [])],
            customer_packs=[CustomerPackRecord(**item) for item in payload.get("customer_packs", [])],
            final_execution=FinalExecutionDiscipline(**payload["final_execution"]),
        )


@dataclass(frozen=True)
class ReadinessSummary:
    overall_ready: bool
    gold_total: int
    gold_passing: int
    gold_failing: int
    gold_blocked: int
    gold_target: int
    gold_target_gap: int
    customer_pack_total: int
    customer_pack_stable: int
    customer_pack_failed: int
    customer_pack_blocked: int
    customer_pack_target: int
    customer_pack_target_gap: int
    final_execution_green: bool
    failing_gates: list[str]
    coverage: dict[str, dict[str, int]]
    blockers: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        coverage_sections: list[str] = []
        for axis in ("domains", "jurisdictions", "frameworks"):
            lines = [f"## Coverage by {axis[:-1].capitalize()}", ""]
            values = self.coverage.get(axis, {})
            if not values:
                lines.append("- none")
            else:
                for key, count in sorted(values.items(), key=lambda item: (-item[1], item[0])):
                    lines.append(f"- {key}: {count}")
            coverage_sections.append("\n".join(lines))

        blockers = self.blockers or ["none"]
        failing = self.failing_gates or ["none"]
        return "\n".join(
            [
                "# Tenet Proof Program Readiness",
                "",
                f"- overall_ready: {'YES' if self.overall_ready else 'NO'}",
                f"- gold_total: {self.gold_total}",
                f"- gold_passing: {self.gold_passing}",
                f"- gold_failing: {self.gold_failing}",
                f"- gold_blocked: {self.gold_blocked}",
                f"- gold_target: {self.gold_target}",
                f"- gold_target_gap: {self.gold_target_gap}",
                f"- customer_pack_total: {self.customer_pack_total}",
                f"- customer_pack_stable: {self.customer_pack_stable}",
                f"- customer_pack_failed: {self.customer_pack_failed}",
                f"- customer_pack_blocked: {self.customer_pack_blocked}",
                f"- customer_pack_target: {self.customer_pack_target}",
                f"- customer_pack_target_gap: {self.customer_pack_target_gap}",
                f"- final_execution_green: {'YES' if self.final_execution_green else 'NO'}",
                f"- failing_gates: {', '.join(failing)}",
                "",
                "## Blockers",
                "",
                *[f"- {item}" for item in blockers],
                "",
                *coverage_sections,
                "",
            ]
        ).strip() + "\n"


class ProofProgramRegistry:
    def __init__(self, state_path: Path = DEFAULT_STATE_PATH) -> None:
        self.state_path = state_path

    def load(self) -> ProofProgramManifest:
        if not self.state_path.exists():
            return ProofProgramManifest.empty()
        payload = _load_json(self.state_path)
        return ProofProgramManifest.from_dict(payload)

    def save(self, manifest: ProofProgramManifest) -> None:
        _atomic_write_json(self.state_path, manifest.to_dict())

    def upsert_gold_case(
        self,
        *,
        case_id: str,
        title: str,
        domain: str,
        jurisdiction: str,
        framework: str,
        control_id: str,
        status: str,
        notes: str | None = None,
        now_epoch: int | None = None,
    ) -> GoldCaseRecord:
        manifest = self.load()
        now = now_epoch or _utc_epoch()
        case_key = _require_non_empty_str(case_id, "case_id")
        existing = {item.case_id: item for item in manifest.gold_cases}
        previous = existing.get(case_key)
        record = GoldCaseRecord(
            case_id=case_key,
            title=_require_non_empty_str(title, "title"),
            domain=_require_non_empty_str(domain, "domain"),
            jurisdiction=_require_non_empty_str(jurisdiction, "jurisdiction"),
            framework=_require_non_empty_str(framework, "framework"),
            control_id=_require_non_empty_str(control_id, "control_id"),
            status=GoldCaseRecord.normalize_status(status),
            created_at_epoch=previous.created_at_epoch if previous else now,
            updated_at_epoch=now,
            notes=_require_non_empty_str(notes, "notes") if isinstance(notes, str) and notes.strip() else None,
        )
        existing[record.case_id] = record
        next_manifest = ProofProgramManifest(
            version=manifest.version,
            gold_target=manifest.gold_target,
            customer_pack_target=manifest.customer_pack_target,
            gold_cases=sorted(existing.values(), key=lambda item: item.case_id),
            customer_packs=manifest.customer_packs,
            final_execution=manifest.final_execution,
        )
        self.save(next_manifest)
        return record

    def upsert_customer_pack(
        self,
        *,
        pack_id: str,
        customer_name: str,
        domain: str,
        jurisdiction: str,
        framework: str,
        status: str,
        notes: str | None = None,
        now_epoch: int | None = None,
    ) -> CustomerPackRecord:
        manifest = self.load()
        now = now_epoch or _utc_epoch()
        pack_key = _require_non_empty_str(pack_id, "pack_id")
        existing = {item.pack_id: item for item in manifest.customer_packs}
        previous = existing.get(pack_key)
        record = CustomerPackRecord(
            pack_id=pack_key,
            customer_name=_require_non_empty_str(customer_name, "customer_name"),
            domain=_require_non_empty_str(domain, "domain"),
            jurisdiction=_require_non_empty_str(jurisdiction, "jurisdiction"),
            framework=_require_non_empty_str(framework, "framework"),
            status=CustomerPackRecord.normalize_status(status),
            created_at_epoch=previous.created_at_epoch if previous else now,
            updated_at_epoch=now,
            notes=_require_non_empty_str(notes, "notes") if isinstance(notes, str) and notes.strip() else None,
        )
        existing[record.pack_id] = record
        next_manifest = ProofProgramManifest(
            version=manifest.version,
            gold_target=manifest.gold_target,
            customer_pack_target=manifest.customer_pack_target,
            gold_cases=manifest.gold_cases,
            customer_packs=sorted(existing.values(), key=lambda item: item.pack_id),
            final_execution=manifest.final_execution,
        )
        self.save(next_manifest)
        return record

    def set_final_execution(
        self,
        *,
        suite_green: bool,
        failing_gate_names: list[str] | None = None,
        ref: str | None = None,
        now_epoch: int | None = None,
    ) -> FinalExecutionDiscipline:
        manifest = self.load()
        discipline = (
            FinalExecutionDiscipline.healthy(ref=ref, now_epoch=now_epoch)
            if suite_green
            else FinalExecutionDiscipline.unhealthy(
                failing_gate_names=failing_gate_names or ["unknown_failure"],
                ref=ref,
                now_epoch=now_epoch,
            )
        )
        next_manifest = ProofProgramManifest(
            version=manifest.version,
            gold_target=manifest.gold_target,
            customer_pack_target=manifest.customer_pack_target,
            gold_cases=manifest.gold_cases,
            customer_packs=manifest.customer_packs,
            final_execution=discipline,
        )
        self.save(next_manifest)
        return discipline

    def set_targets(self, *, gold_target: int, customer_pack_target: int) -> ProofProgramManifest:
        if not isinstance(gold_target, int) or gold_target <= 0:
            raise ValueError("gold_target must be positive")
        if not isinstance(customer_pack_target, int) or customer_pack_target <= 0:
            raise ValueError("customer_pack_target must be positive")
        manifest = self.load()
        next_manifest = ProofProgramManifest(
            version=manifest.version,
            gold_target=gold_target,
            customer_pack_target=customer_pack_target,
            gold_cases=manifest.gold_cases,
            customer_packs=manifest.customer_packs,
            final_execution=manifest.final_execution,
        )
        self.save(next_manifest)
        return next_manifest

    def summarize(self) -> ReadinessSummary:
        manifest = self.load()
        gold_total = len(manifest.gold_cases)
        gold_passing = sum(1 for item in manifest.gold_cases if item.status == "PASS")
        gold_failing = sum(1 for item in manifest.gold_cases if item.status == "FAIL")
        gold_blocked = sum(1 for item in manifest.gold_cases if item.status == "BLOCKED")

        customer_pack_total = len(manifest.customer_packs)
        customer_pack_stable = sum(1 for item in manifest.customer_packs if item.status in {"ACTIVE", "STABLE"})
        customer_pack_failed = sum(1 for item in manifest.customer_packs if item.status == "FAILED")
        customer_pack_blocked = sum(1 for item in manifest.customer_packs if item.status == "BLOCKED")

        coverage = {
            "domains": self._coverage_counts(manifest, axis="domain"),
            "jurisdictions": self._coverage_counts(manifest, axis="jurisdiction"),
            "frameworks": self._coverage_counts(manifest, axis="framework"),
        }

        blockers: list[str] = []
        gold_target_gap = max(manifest.gold_target - gold_total, 0)
        customer_pack_target_gap = max(manifest.customer_pack_target - customer_pack_total, 0)

        if gold_failing > 0:
            blockers.append(f"{gold_failing} gold case(s) failing")
        if gold_blocked > 0:
            blockers.append(f"{gold_blocked} gold case(s) blocked")
        if gold_target_gap > 0:
            blockers.append(f"gold case target gap: {gold_target_gap}")

        if customer_pack_failed > 0:
            blockers.append(f"{customer_pack_failed} customer pack(s) failed")
        if customer_pack_blocked > 0:
            blockers.append(f"{customer_pack_blocked} customer pack(s) blocked")
        if customer_pack_target_gap > 0:
            blockers.append(f"customer pack target gap: {customer_pack_target_gap}")

        if not manifest.final_execution.suite_green:
            blockers.append(
                "final execution discipline not green: "
                + ", ".join(manifest.final_execution.failing_gate_names)
            )

        return ReadinessSummary(
            overall_ready=not blockers,
            gold_total=gold_total,
            gold_passing=gold_passing,
            gold_failing=gold_failing,
            gold_blocked=gold_blocked,
            gold_target=manifest.gold_target,
            gold_target_gap=gold_target_gap,
            customer_pack_total=customer_pack_total,
            customer_pack_stable=customer_pack_stable,
            customer_pack_failed=customer_pack_failed,
            customer_pack_blocked=customer_pack_blocked,
            customer_pack_target=manifest.customer_pack_target,
            customer_pack_target_gap=customer_pack_target_gap,
            final_execution_green=manifest.final_execution.suite_green,
            failing_gates=manifest.final_execution.failing_gate_names,
            coverage=coverage,
            blockers=blockers,
        )

    def write_readiness_outputs(
        self,
        *,
        json_path: Path = DEFAULT_SUMMARY_JSON_PATH,
        markdown_path: Path = DEFAULT_SUMMARY_MD_PATH,
    ) -> ReadinessSummary:
        summary = self.summarize()
        _atomic_write_json(json_path, summary.to_dict())
        _atomic_write_text(markdown_path, summary.to_markdown())
        return summary

    @staticmethod
    def _coverage_counts(
        manifest: ProofProgramManifest,
        *,
        axis: str,
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in manifest.gold_cases:
            key = getattr(item, axis)
            counts[key] = counts.get(key, 0) + 1
        return counts


def load_registry(path: str | None = None) -> ProofProgramRegistry:
    return ProofProgramRegistry(Path(path) if path else DEFAULT_STATE_PATH)
