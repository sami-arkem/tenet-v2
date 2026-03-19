from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from core.audit_schedule_policy import (
    AuditSchedulePolicy,
    DueExecutionAction,
    SkipReason,
    evaluate_due_execution,
    evaluate_reminder,
    policy_from_dict,
)


RUNTIME_SCHEMA_VERSION = "1.0"


def _stable_json_hash(payload: Dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _iso_to_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


@dataclass(frozen=True)
class MaterializedAuditExecution:
    execution_id: str
    schedule_id: str
    tenant_id: str
    audit_kind: str
    due_date: str
    execution_date: str
    execution_key: str
    source_policy_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class NotificationEvent:
    event_id: str
    schedule_id: str
    tenant_id: str
    audit_kind: str
    event_kind: str
    target_date: str
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ScheduleSkipRecord:
    schedule_id: str
    tenant_id: str
    audit_kind: str
    due_date: Optional[str]
    skip_reason: str
    stale_evidence: bool

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeCycleResult:
    schema_version: str
    cycle_date: str
    executions: List[MaterializedAuditExecution] = field(default_factory=list)
    reminder_events: List[NotificationEvent] = field(default_factory=list)
    skip_events: List[NotificationEvent] = field(default_factory=list)
    skipped: List[ScheduleSkipRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "cycle_date": self.cycle_date,
            "executions": [item.to_dict() for item in self.executions],
            "reminder_events": [item.to_dict() for item in self.reminder_events],
            "skip_events": [item.to_dict() for item in self.skip_events],
            "skipped": [item.to_dict() for item in self.skipped],
        }


@dataclass(frozen=True)
class RuntimeState:
    materialized_execution_keys: List[str] = field(default_factory=list)
    emitted_notification_keys: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "materialized_execution_keys": sorted(set(self.materialized_execution_keys)),
            "emitted_notification_keys": sorted(set(self.emitted_notification_keys)),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "RuntimeState":
        return cls(
            materialized_execution_keys=[
                str(x) for x in payload.get("materialized_execution_keys", [])
            ],
            emitted_notification_keys=[
                str(x) for x in payload.get("emitted_notification_keys", [])
            ],
        )


def _policy_hash(policy: AuditSchedulePolicy) -> str:
    payload = {
        "schedule_id": policy.schedule_id,
        "tenant_id": policy.tenant_id,
        "audit_kind": policy.audit_kind,
        "frequency": policy.frequency.value,
        "effective_from": policy.effective_from,
        "enabled": policy.enabled,
        "custom_interval_days": policy.custom_interval_days,
        "last_run_at": policy.last_run_at,
        "last_evidence_refresh_at": policy.last_evidence_refresh_at,
        "notes": policy.notes,
    }
    return _stable_json_hash(payload)


def _execution_key(policy: AuditSchedulePolicy, due_date: str) -> str:
    return f"{policy.tenant_id}:{policy.audit_kind}:{policy.schedule_id}:{due_date}"


def _notification_key(
    *,
    schedule_id: str,
    tenant_id: str,
    audit_kind: str,
    event_kind: str,
    target_date: str,
) -> str:
    return f"{tenant_id}:{audit_kind}:{schedule_id}:{event_kind}:{target_date}"


def _notification_event(
    *,
    schedule_id: str,
    tenant_id: str,
    audit_kind: str,
    event_kind: str,
    target_date: str,
) -> NotificationEvent:
    key = _notification_key(
        schedule_id=schedule_id,
        tenant_id=tenant_id,
        audit_kind=audit_kind,
        event_kind=event_kind,
        target_date=target_date,
    )
    return NotificationEvent(
        event_id=key,
        schedule_id=schedule_id,
        tenant_id=tenant_id,
        audit_kind=audit_kind,
        event_kind=event_kind,
        target_date=target_date,
        payload_hash=_stable_json_hash({
            "schedule_id": schedule_id,
            "tenant_id": tenant_id,
            "audit_kind": audit_kind,
            "event_kind": event_kind,
            "target_date": target_date,
        }),
    )


def _skip_record(decision: DueExecutionDecision) -> ScheduleSkipRecord:
    return ScheduleSkipRecord(
        schedule_id=decision.schedule_id,
        tenant_id=decision.tenant_id,
        audit_kind=decision.audit_kind,
        due_date=decision.due_date,
        skip_reason=decision.skip_reason.value if decision.skip_reason else "UNKNOWN",
        stale_evidence=decision.stale_evidence,
    )


def load_runtime_state(path: Path) -> RuntimeState:
    if not path.exists():
        return RuntimeState()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RuntimeState.from_dict(payload)


def save_runtime_state(path: Path, state: RuntimeState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_policies(path: Path) -> List[AuditSchedulePolicy]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("policy input must be a list")
    policies = [policy_from_dict(item) for item in raw]
    policies.sort(key=lambda item: (item.tenant_id, item.audit_kind, item.schedule_id))
    return policies


def run_schedule_cycle(
    policies: Sequence[AuditSchedulePolicy],
    *,
    cycle_date: date,
    state: Optional[RuntimeState] = None,
) -> Tuple[RuntimeCycleResult, RuntimeState]:
    runtime_state = state or RuntimeState()
    materialized_keys = set(runtime_state.materialized_execution_keys)
    emitted_notification_keys = set(runtime_state.emitted_notification_keys)

    executions: List[MaterializedAuditExecution] = []
    reminder_events: List[NotificationEvent] = []
    skip_events: List[NotificationEvent] = []
    skipped: List[ScheduleSkipRecord] = []

    for policy in policies:
        decision = evaluate_due_execution(policy, cycle_date)
        reminder = evaluate_reminder(policy, cycle_date)

        if reminder.should_remind and reminder.reminder_for_date is not None:
            reminder_key = _notification_key(
                schedule_id=policy.schedule_id,
                tenant_id=policy.tenant_id,
                audit_kind=policy.audit_kind,
                event_kind="AUDIT_REMINDER",
                target_date=reminder.reminder_for_date,
            )
            if reminder_key not in emitted_notification_keys:
                reminder_events.append(_notification_event(
                    schedule_id=policy.schedule_id,
                    tenant_id=policy.tenant_id,
                    audit_kind=policy.audit_kind,
                    event_kind="AUDIT_REMINDER",
                    target_date=reminder.reminder_for_date,
                ))
                emitted_notification_keys.add(reminder_key)

        if decision.action == DueExecutionAction.MATERIALIZE:
            assert decision.due_date is not None
            execution_key = _execution_key(policy, decision.due_date)
            if execution_key not in materialized_keys:
                executions.append(MaterializedAuditExecution(
                    execution_id=execution_key,
                    schedule_id=policy.schedule_id,
                    tenant_id=policy.tenant_id,
                    audit_kind=policy.audit_kind,
                    due_date=decision.due_date,
                    execution_date=cycle_date.isoformat(),
                    execution_key=execution_key,
                    source_policy_hash=_policy_hash(policy),
                ))
                materialized_keys.add(execution_key)
        else:
            skipped.append(_skip_record(decision))
            if decision.skip_reason in {SkipReason.STALE_EVIDENCE, SkipReason.INVALID_CONFIGURATION}:
                target_date = decision.due_date or cycle_date.isoformat()
                skip_key = _notification_key(
                    schedule_id=policy.schedule_id,
                    tenant_id=policy.tenant_id,
                    audit_kind=policy.audit_kind,
                    event_kind=f"SCHEDULE_{decision.skip_reason.value}",
                    target_date=target_date,
                )
                if skip_key not in emitted_notification_keys:
                    skip_events.append(_notification_event(
                        schedule_id=policy.schedule_id,
                        tenant_id=policy.tenant_id,
                        audit_kind=policy.audit_kind,
                        event_kind=f"SCHEDULE_{decision.skip_reason.value}",
                        target_date=target_date,
                    ))
                    emitted_notification_keys.add(skip_key)

    executions.sort(key=lambda item: (item.tenant_id, item.audit_kind, item.schedule_id, item.due_date))
    reminder_events.sort(key=lambda item: (item.tenant_id, item.audit_kind, item.schedule_id, item.target_date, item.event_kind))
    skip_events.sort(key=lambda item: (item.tenant_id, item.audit_kind, item.schedule_id, item.target_date, item.event_kind))
    skipped.sort(key=lambda item: (item.tenant_id, item.audit_kind, item.schedule_id, item.skip_reason, item.due_date or ""))

    result = RuntimeCycleResult(
        schema_version=RUNTIME_SCHEMA_VERSION,
        cycle_date=cycle_date.isoformat(),
        executions=executions,
        reminder_events=reminder_events,
        skip_events=skip_events,
        skipped=skipped,
    )

    next_state = RuntimeState(
        materialized_execution_keys=sorted(materialized_keys),
        emitted_notification_keys=sorted(emitted_notification_keys),
    )

    return result, next_state


def write_cycle_artifacts(
    *,
    output_path: Path,
    state_path: Path,
    result: RuntimeCycleResult,
    state: RuntimeState,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    save_runtime_state(state_path, state)
