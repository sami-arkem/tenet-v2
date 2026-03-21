from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional


STALE_EVIDENCE_DAYS = 60
REMINDER_LEAD_DAYS = 7


class ScheduleFrequency(str, Enum):
    MANUAL = "MANUAL"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    BIANNUAL = "BIANNUAL"
    ANNUAL = "ANNUAL"
    CUSTOM = "CUSTOM"


class DueExecutionAction(str, Enum):
    MATERIALIZE = "MATERIALIZE"
    SKIP = "SKIP"


class SkipReason(str, Enum):
    NOT_DUE = "NOT_DUE"
    MANUAL_SCHEDULE = "MANUAL_SCHEDULE"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    SCHEDULE_DISABLED = "SCHEDULE_DISABLED"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"


def _iso_to_date(value: Optional[str]) -> Optional[date]:
    if value is None:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _date_to_iso(value: Optional[date]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat()


def _add_months(anchor: date, months: int) -> date:
    month_index = (anchor.month - 1) + months
    year = anchor.year + (month_index // 12)
    month = (month_index % 12) + 1
    if month == 2:
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        max_day = 29 if leap else 28
    elif month in (4, 6, 9, 11):
        max_day = 30
    else:
        max_day = 31
    day = min(anchor.day, max_day)
    return date(year, month, day)


@dataclass(frozen=True)
class AuditSchedulePolicy:
    schedule_id: str
    tenant_id: str
    audit_kind: str
    frequency: ScheduleFrequency
    effective_from: str
    enabled: bool = True
    custom_interval_days: Optional[int] = None
    last_run_at: Optional[str] = None
    last_evidence_refresh_at: Optional[str] = None
    notes: Optional[str] = None

    def validate(self) -> None:
        if not self.schedule_id.strip():
            raise ValueError("schedule_id is required")
        if not self.tenant_id.strip():
            raise ValueError("tenant_id is required")
        if not self.audit_kind.strip():
            raise ValueError("audit_kind is required")
        effective = _iso_to_date(self.effective_from)
        if effective is None:
            raise ValueError("effective_from is required")
        if self.frequency == ScheduleFrequency.CUSTOM:
            if self.custom_interval_days is None:
                raise ValueError("custom_interval_days required for CUSTOM")
            if self.custom_interval_days <= 0:
                raise ValueError("custom_interval_days must be positive")
        else:
            if self.custom_interval_days is not None:
                raise ValueError("custom_interval_days only allowed for CUSTOM")
        if self.last_run_at is not None:
            _iso_to_date(self.last_run_at)
        if self.last_evidence_refresh_at is not None:
            _iso_to_date(self.last_evidence_refresh_at)

    def anchor_date(self) -> date:
        return _iso_to_date(self.last_run_at) or _iso_to_date(self.effective_from)

    def next_due_date(self, today: date) -> Optional[date]:
        self.validate()
        if not self.enabled:
            return None
        if self.frequency == ScheduleFrequency.MANUAL:
            return None
        anchor = self.anchor_date()
        if self.frequency == ScheduleFrequency.MONTHLY:
            candidate = _add_months(anchor, 1)
        elif self.frequency == ScheduleFrequency.QUARTERLY:
            candidate = _add_months(anchor, 3)
        elif self.frequency == ScheduleFrequency.BIANNUAL:
            candidate = _add_months(anchor, 6)
        elif self.frequency == ScheduleFrequency.ANNUAL:
            candidate = _add_months(anchor, 12)
        elif self.frequency == ScheduleFrequency.CUSTOM:
            candidate = anchor + timedelta(days=int(self.custom_interval_days or 0))
        else:
            raise ValueError(f"unsupported frequency: {self.frequency}")
        while candidate < today:
            if self.frequency == ScheduleFrequency.MONTHLY:
                candidate = _add_months(candidate, 1)
            elif self.frequency == ScheduleFrequency.QUARTERLY:
                candidate = _add_months(candidate, 3)
            elif self.frequency == ScheduleFrequency.BIANNUAL:
                candidate = _add_months(candidate, 6)
            elif self.frequency == ScheduleFrequency.ANNUAL:
                candidate = _add_months(candidate, 12)
            elif self.frequency == ScheduleFrequency.CUSTOM:
                candidate = candidate + timedelta(days=int(self.custom_interval_days or 0))
            else:
                break
        return candidate

    def reminder_date(self, today: date) -> Optional[date]:
        due = self.next_due_date(today)
        if due is None:
            return None
        return due - timedelta(days=REMINDER_LEAD_DAYS)

    def evidence_is_stale(self, today: date) -> bool:
        if self.last_evidence_refresh_at is None:
            return True
        evidence_date = _iso_to_date(self.last_evidence_refresh_at)
        assert evidence_date is not None
        age_days = (today - evidence_date).days
        return age_days > STALE_EVIDENCE_DAYS


@dataclass(frozen=True)
class ScheduleReminderDecision:
    schedule_id: str
    should_remind: bool
    reminder_for_date: Optional[str]
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DueExecutionDecision:
    schedule_id: str
    tenant_id: str
    audit_kind: str
    action: DueExecutionAction
    due_date: Optional[str]
    skip_reason: Optional[SkipReason]
    stale_evidence: bool
    frequency: str

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["action"] = self.action.value
        payload["skip_reason"] = self.skip_reason.value if self.skip_reason else None
        return payload


@dataclass(frozen=True)
class DueExecutionBatch:
    materialized: List[DueExecutionDecision] = field(default_factory=list)
    skipped: List[DueExecutionDecision] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "materialized": [item.to_dict() for item in self.materialized],
            "skipped": [item.to_dict() for item in self.skipped],
        }


def evaluate_reminder(policy: AuditSchedulePolicy, today: date) -> ScheduleReminderDecision:
    try:
        policy.validate()
    except Exception:
        return ScheduleReminderDecision(
            schedule_id=policy.schedule_id,
            should_remind=False,
            reminder_for_date=None,
            reason="invalid_configuration",
        )
    if not policy.enabled:
        return ScheduleReminderDecision(
            schedule_id=policy.schedule_id,
            should_remind=False,
            reminder_for_date=None,
            reason="schedule_disabled",
        )
    due_date = policy.next_due_date(today)
    if due_date is None:
        return ScheduleReminderDecision(
            schedule_id=policy.schedule_id,
            should_remind=False,
            reminder_for_date=None,
            reason="manual_or_non_due_schedule",
        )
    reminder_date = due_date - timedelta(days=REMINDER_LEAD_DAYS)
    should_remind = today >= reminder_date and today <= due_date
    return ScheduleReminderDecision(
        schedule_id=policy.schedule_id,
        should_remind=should_remind,
        reminder_for_date=_date_to_iso(due_date),
        reason=None if should_remind else "outside_reminder_window",
    )


def evaluate_due_execution(policy: AuditSchedulePolicy, today: date) -> DueExecutionDecision:
    try:
        policy.validate()
    except Exception:
        return DueExecutionDecision(
            schedule_id=policy.schedule_id,
            tenant_id=policy.tenant_id,
            audit_kind=policy.audit_kind,
            action=DueExecutionAction.SKIP,
            due_date=None,
            skip_reason=SkipReason.INVALID_CONFIGURATION,
            stale_evidence=True,
            frequency=policy.frequency.value,
        )
    if not policy.enabled:
        return DueExecutionDecision(
            schedule_id=policy.schedule_id,
            tenant_id=policy.tenant_id,
            audit_kind=policy.audit_kind,
            action=DueExecutionAction.SKIP,
            due_date=None,
            skip_reason=SkipReason.SCHEDULE_DISABLED,
            stale_evidence=policy.evidence_is_stale(today),
            frequency=policy.frequency.value,
        )
    if policy.frequency == ScheduleFrequency.MANUAL:
        return DueExecutionDecision(
            schedule_id=policy.schedule_id,
            tenant_id=policy.tenant_id,
            audit_kind=policy.audit_kind,
            action=DueExecutionAction.SKIP,
            due_date=None,
            skip_reason=SkipReason.MANUAL_SCHEDULE,
            stale_evidence=policy.evidence_is_stale(today),
            frequency=policy.frequency.value,
        )
    due_date = policy.next_due_date(today)
    stale = policy.evidence_is_stale(today)
    if due_date is None or today < due_date:
        return DueExecutionDecision(
            schedule_id=policy.schedule_id,
            tenant_id=policy.tenant_id,
            audit_kind=policy.audit_kind,
            action=DueExecutionAction.SKIP,
            due_date=_date_to_iso(due_date),
            skip_reason=SkipReason.NOT_DUE,
            stale_evidence=stale,
            frequency=policy.frequency.value,
        )
    if stale:
        return DueExecutionDecision(
            schedule_id=policy.schedule_id,
            tenant_id=policy.tenant_id,
            audit_kind=policy.audit_kind,
            action=DueExecutionAction.SKIP,
            due_date=_date_to_iso(due_date),
            skip_reason=SkipReason.STALE_EVIDENCE,
            stale_evidence=True,
            frequency=policy.frequency.value,
        )
    return DueExecutionDecision(
        schedule_id=policy.schedule_id,
        tenant_id=policy.tenant_id,
        audit_kind=policy.audit_kind,
        action=DueExecutionAction.MATERIALIZE,
        due_date=_date_to_iso(due_date),
        skip_reason=None,
        stale_evidence=False,
        frequency=policy.frequency.value,
    )


def materialize_due_executions(
    policies: List[AuditSchedulePolicy],
    today: date,
) -> DueExecutionBatch:
    materialized: List[DueExecutionDecision] = []
    skipped: List[DueExecutionDecision] = []
    for policy in policies:
        decision = evaluate_due_execution(policy, today)
        if decision.action == DueExecutionAction.MATERIALIZE:
            materialized.append(decision)
        else:
            skipped.append(decision)
    materialized.sort(key=lambda item: (item.tenant_id, item.audit_kind, item.schedule_id))
    skipped.sort(key=lambda item: (item.tenant_id, item.audit_kind, item.schedule_id))
    return DueExecutionBatch(materialized=materialized, skipped=skipped)


def policy_from_dict(payload: Dict[str, object]) -> AuditSchedulePolicy:
    frequency_raw = str(payload["frequency"]).strip().upper()
    return AuditSchedulePolicy(
        schedule_id=str(payload["schedule_id"]),
        tenant_id=str(payload["tenant_id"]),
        audit_kind=str(payload["audit_kind"]),
        frequency=ScheduleFrequency(frequency_raw),
        effective_from=str(payload["effective_from"]),
        enabled=bool(payload.get("enabled", True)),
        custom_interval_days=(
            int(payload["custom_interval_days"])
            if payload.get("custom_interval_days") is not None
            else None
        ),
        last_run_at=(
            str(payload["last_run_at"])
            if payload.get("last_run_at") is not None
            else None
        ),
        last_evidence_refresh_at=(
            str(payload["last_evidence_refresh_at"])
            if payload.get("last_evidence_refresh_at") is not None
            else None
        ),
        notes=str(payload["notes"]) if payload.get("notes") is not None else None,
    )
