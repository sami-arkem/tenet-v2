"""
Database query functions.
Bible Rule 4: every query includes tenant_id filter.
Bible Rule 4: RLS context is set by set_tenant_context() before any query.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .connection import set_tenant_context


# ─── Audit Runs ──────────────────────────────────────────────────────────────


async def get_audit_run(
    db: AsyncSession,
    *,
    run_id: str,
    tenant_id: str,
) -> dict[str, Any] | None:
    """Get single audit run, enforcing tenant isolation at query level."""
    result = await db.execute(
        text(
            """
            SELECT id, tenant_id, entity_id, status, jurisdiction, regime_scope,
                   overall_verdict, posture, control_count, pass_count, partial_count,
                   fail_count, missing_count, na_count, started_by, started_at,
                   completed_at, duration_seconds, gold_case_version, model_version,
                   error_message, created_at, updated_at,
                   system_name, audit_kind, framework, deployment_decision,
                   release_ready, note
            FROM audit_runs
            WHERE id = :run_id AND tenant_id = :tenant_id
            """
        ),
        {"run_id": run_id, "tenant_id": tenant_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def list_audit_runs(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    filters = ["tenant_id = :tenant_id"]
    params: dict[str, Any] = {"tenant_id": tenant_id, "limit": limit, "offset": offset}

    if entity_id:
        filters.append("entity_id = :entity_id")
        params["entity_id"] = entity_id
    if status:
        filters.append("status = :status")
        params["status"] = status

    where = " AND ".join(filters)

    result = await db.execute(
        text(
            f"""
            SELECT id, tenant_id, entity_id, status, jurisdiction, regime_scope,
                   overall_verdict, posture, control_count, pass_count, partial_count,
                   fail_count, missing_count, na_count, started_at, completed_at,
                   duration_seconds, model_version, created_at, updated_at,
                   system_name, audit_kind, framework, deployment_decision,
                   release_ready, note
            FROM audit_runs
            WHERE {where}
            ORDER BY created_at DESC NULLS LAST
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    items = [dict(row) for row in result.mappings().all()]

    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM audit_runs WHERE {where}"),
        {k: v for k, v in params.items() if k not in ("limit", "offset")},
    )
    total = count_result.scalar_one()

    return {"items": items, "total": total}


async def get_running_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_id: str | None = None,
) -> dict[str, Any] | None:
    params: dict[str, Any] = {"tenant_id": tenant_id}
    entity_filter = ""
    if entity_id:
        entity_filter = "AND entity_id = :entity_id"
        params["entity_id"] = entity_id

    result = await db.execute(
        text(
            f"""
            SELECT id, status FROM audit_runs
            WHERE tenant_id = :tenant_id
              AND status IN ('PENDING', 'RUNNING')
              {entity_filter}
            LIMIT 1
            """
        ),
        params,
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def create_audit_run(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_id: str | None,
    system_name: str = "Untitled System",
    audit_kind: str = "compliance_audit",
    framework: str = "",
    jurisdiction: str,
    regime_scope: list[str],
    company_profile: dict,
    evidence_ids: list[str],
    started_by: str,
    note: str | None = None,
    gold_case_version: str | None = None,
    model_version: str = "claude-sonnet-4-6",
) -> dict[str, Any]:
    run_id = str(uuid.uuid4())

    await db.execute(
        text(
            """
            INSERT INTO audit_runs (
                id, tenant_id, entity_id, status, jurisdiction, regime_scope,
                company_profile, evidence_ids, started_by, gold_case_version, model_version,
                system_name, audit_kind, framework, note, started_at
            ) VALUES (
                :id, :tenant_id, :entity_id, 'CREATED', :jurisdiction, :regime_scope,
                :company_profile, :evidence_ids, :started_by, :gold_case_version, :model_version,
                :system_name, :audit_kind, :framework, :note, NOW()
            )
            """
        ),
        {
            "id": run_id,
            "tenant_id": tenant_id,
            "entity_id": entity_id,
            "jurisdiction": jurisdiction,
            "regime_scope": ",".join(regime_scope) if regime_scope else "",
            "company_profile": __import__("json").dumps(company_profile),
            "evidence_ids": [str(e) for e in evidence_ids],
            "started_by": started_by,
            "gold_case_version": gold_case_version,
            "model_version": model_version,
            "system_name": system_name,
            "audit_kind": audit_kind,
            "framework": framework,
            "note": note,
        },
    )
    return await get_audit_run(db, run_id=run_id, tenant_id=tenant_id)  # type: ignore[return-value]


async def update_audit_run_status(
    db: AsyncSession,
    *,
    run_id: str,
    tenant_id: str,
    status: str,
    overall_verdict: str | None = None,
    posture: str | None = None,
    pass_count: int = 0,
    partial_count: int = 0,
    fail_count: int = 0,
    missing_count: int = 0,
    na_count: int = 0,
    control_count: int = 0,
    error_message: str | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    completed_at = now if status in ("COMPLETE", "FAILED", "PARTIAL", "CANCELLED") else None
    started_at_raw = await db.execute(
        text("SELECT started_at FROM audit_runs WHERE id = :id AND tenant_id = :tid"),
        {"id": run_id, "tid": tenant_id},
    )
    row = started_at_raw.first()
    duration = None
    if row and completed_at:
        started = row[0]
        if started and hasattr(started, 'replace'):
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
        diff = completed_at - started if started else None
        duration = int(diff.total_seconds()) if diff else None

    await db.execute(
        text(
            """
            UPDATE audit_runs SET
                status = :status,
                overall_verdict = :overall_verdict,
                posture = :posture,
                control_count = :control_count,
                pass_count = :pass_count,
                partial_count = :partial_count,
                fail_count = :fail_count,
                missing_count = :missing_count,
                na_count = :na_count,
                completed_at = :completed_at,
                duration_seconds = :duration,
                error_message = :error_message,
                updated_at = NOW()
            WHERE id = :run_id AND tenant_id = :tenant_id
            """
        ),
        {
            "status": status,
            "overall_verdict": overall_verdict,
            "posture": posture,
            "control_count": control_count,
            "pass_count": pass_count,
            "partial_count": partial_count,
            "fail_count": fail_count,
            "missing_count": missing_count,
            "na_count": na_count,
            "completed_at": completed_at,
            "duration": duration,
            "error_message": error_message,
            "run_id": run_id,
            "tenant_id": tenant_id,
        },
    )


# ─── Findings ────────────────────────────────────────────────────────────────

# Valid status transitions — Bible §T.2.7
VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "OPEN":               {"IN_PROGRESS"},
    "IN_PROGRESS":        {"EVIDENCE_SUBMITTED", "OPEN"},
    "EVIDENCE_SUBMITTED": {"IN_PROGRESS", "VERIFYING"},
    "VERIFYING":          {"CLOSED", "IN_PROGRESS"},
    "CLOSED":             {"OPEN"},
    "EXCEPTION":          set(),
    "DISMISSED":          set(),
}


async def list_findings(
    db: AsyncSession,
    *,
    tenant_id: str,
    audit_run_id: str | None = None,
    verdict: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    regime: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    filters = ["tenant_id = :tenant_id"]
    params: dict[str, Any] = {"tenant_id": tenant_id, "limit": limit, "offset": offset}

    if audit_run_id:
        filters.append("audit_run_id = :audit_run_id")
        params["audit_run_id"] = audit_run_id
    if verdict:
        filters.append("verdict = :verdict")
        params["verdict"] = verdict
    if severity:
        filters.append("severity = :severity")
        params["severity"] = severity
    if status:
        filters.append("status = :status")
        params["status"] = status
    if regime:
        filters.append("regime = :regime")
        params["regime"] = regime
    if search:
        filters.append(
            "(control_name ILIKE :search OR control_id ILIKE :search OR finding ILIKE :search)"
        )
        params["search"] = f"%{search}%"

    where = " AND ".join(filters)
    severity_order = "CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 WHEN 'LOW' THEN 4 END"

    result = await db.execute(
        text(
            f"""
            SELECT id, tenant_id, audit_run_id, control_id, control_name, regime, jurisdiction,
                   verdict, severity, status, finding, requirement, gap, risk,
                   recommended_action, regulatory_reference, assigned_to, due_date,
                   notes, created_at, updated_at
            FROM findings
            WHERE {where}
            ORDER BY {severity_order} ASC, created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    items = [dict(row) for row in result.mappings().all()]
    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM findings WHERE {where}"),
        {k: v for k, v in params.items() if k not in ("limit", "offset")},
    )
    total = count_result.scalar_one()
    return {"items": items, "total": total}


async def get_finding(
    db: AsyncSession, *, finding_id: str, tenant_id: str
) -> dict[str, Any] | None:
    result = await db.execute(
        text(
            """
            SELECT id, tenant_id, audit_run_id, control_id, control_name, regime, jurisdiction,
                   verdict, severity, status, finding, requirement, gap, risk,
                   recommended_action, regulatory_reference, assigned_to, due_date,
                   notes, created_at, updated_at
            FROM findings
            WHERE id = :id AND tenant_id = :tenant_id
            """
        ),
        {"id": finding_id, "tenant_id": tenant_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def update_finding(
    db: AsyncSession,
    *,
    finding_id: str,
    tenant_id: str,
    user_id: str,
    status: str | None = None,
    assigned_to: str | None = None,
    due_date: Any | None = None,
    notes: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    current = await get_finding(db, finding_id=finding_id, tenant_id=tenant_id)
    if not current:
        raise ValueError("FINDING_NOT_FOUND")

    if status and status != current["status"]:
        allowed = VALID_STATUS_TRANSITIONS.get(current["status"], set())
        if status not in allowed:
            raise ValueError(
                f"FINDING_INVALID_STATUS: cannot move from {current['status']} to {status}"
            )
        if not note or len(note.strip()) < 10:
            raise ValueError("FINDING_NOTE_REQUIRED")

    fields: list[str] = []
    params: dict[str, Any] = {"id": finding_id, "tenant_id": tenant_id}

    if status:
        fields.append("status = :status")
        params["status"] = status
        if status == "CLOSED":
            fields.append("closed_at = NOW()")
            fields.append("closed_by = :closed_by")
            params["closed_by"] = user_id
    if assigned_to is not None:
        fields.append("assigned_to = :assigned_to")
        params["assigned_to"] = assigned_to
    if due_date is not None:
        fields.append("due_date = :due_date")
        params["due_date"] = due_date
    if notes is not None:
        fields.append("notes = :notes")
        params["notes"] = notes

    if fields:
        await db.execute(
            text(
                f"UPDATE findings SET {', '.join(fields)}, updated_at = NOW() "
                "WHERE id = :id AND tenant_id = :tenant_id"
            ),
            params,
        )

    # Write activity log entry
    from_status = current["status"] if status else None
    await db.execute(
        text(
            """
            INSERT INTO findings_activity (tenant_id, finding_id, actor_type, actor_id,
                action, from_status, to_status, note)
            VALUES (:tenant_id, :finding_id, 'user', :actor_id,
                :action, :from_status, :to_status, :note)
            """
        ),
        {
            "tenant_id": tenant_id,
            "finding_id": finding_id,
            "actor_id": user_id,
            "action": "STATUS_CHANGED" if status else "UPDATED",
            "from_status": from_status,
            "to_status": status,
            "note": note or notes or "",
        },
    )

    updated = await get_finding(db, finding_id=finding_id, tenant_id=tenant_id)
    return updated  # type: ignore[return-value]


async def insert_findings_from_verdicts(
    db: AsyncSession,
    *,
    tenant_id: str,
    audit_run_id: str,
    entity_id: str | None,
    verdicts: list[dict[str, Any]],
) -> None:
    """Bulk-insert findings derived from control verdicts (non-PASS only)."""
    for v in verdicts:
        if v.get("verdict") == "PASS":
            continue
        await db.execute(
            text(
                """
                INSERT INTO findings (
                    tenant_id, audit_run_id,
                    control_id, control_name, regime, jurisdiction, verdict, severity,
                    finding, requirement, gap, risk, recommended_action, regulatory_reference,
                    status
                ) VALUES (
                    :tenant_id, :audit_run_id,
                    :control_id, :control_name, :regime, :jurisdiction, :verdict, :severity,
                    :finding, :requirement, :gap, :risk, :recommended_action, :regulatory_reference,
                    'OPEN'
                )
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "tenant_id": tenant_id,
                "audit_run_id": audit_run_id,
                "control_id": v.get("control_id", ""),
                "control_name": v.get("control_name", ""),
                "regime": v.get("regime", ""),
                "jurisdiction": v.get("jurisdiction", ""),
                "verdict": v.get("verdict", "FAIL"),
                "severity": v.get("severity", "MEDIUM"),
                "finding": v.get("finding", ""),
                "requirement": v.get("requirement"),
                "gap": v.get("gap"),
                "risk": v.get("risk"),
                "recommended_action": v.get("recommended_action"),
                "regulatory_reference": v.get("regulatory_reference"),
            },
        )


# ─── Dashboard ───────────────────────────────────────────────────────────────

async def get_dashboard_metrics(
    db: AsyncSession, *, tenant_id: str
) -> dict[str, Any]:
    """
    Compute real-time dashboard metrics from findings and audit_runs.
    For production with high volume, these would be pre-computed in dashboard_cache.
    """
    open_result = await db.execute(
        text(
            """
            SELECT
                COUNT(*) FILTER (WHERE status != 'CLOSED' AND status != 'DISMISSED') AS open_total,
                COUNT(*) FILTER (WHERE severity = 'CRITICAL' AND status != 'CLOSED') AS critical,
                COUNT(*) FILTER (WHERE severity = 'HIGH' AND status != 'CLOSED') AS high
            FROM findings
            WHERE tenant_id = :tenant_id
            """
        ),
        {"tenant_id": tenant_id},
    )
    open_row = open_result.mappings().first() or {}

    verdicts_result = await db.execute(
        text(
            """
            SELECT
                COUNT(*) FILTER (WHERE verdict = 'PASS') AS passing,
                COUNT(*) AS total
            FROM control_verdicts
            WHERE tenant_id = :tenant_id
            """
        ),
        {"tenant_id": tenant_id},
    )
    verdicts_row = verdicts_result.mappings().first() or {}

    last_audit_result = await db.execute(
        text(
            """
            SELECT id, status, posture, completed_at
            FROM audit_runs
            WHERE tenant_id = :tenant_id AND status = 'COMPLETE'
            ORDER BY completed_at DESC
            LIMIT 1
            """
        ),
        {"tenant_id": tenant_id},
    )
    last_audit = last_audit_result.mappings().first()

    regime_health_result = await db.execute(
        text(
            """
            SELECT regime,
                   COUNT(*) FILTER (WHERE verdict = 'PASS') AS pass_count,
                   COUNT(*) FILTER (WHERE verdict = 'PARTIAL') AS partial_count,
                   COUNT(*) FILTER (WHERE verdict = 'FAIL') AS fail_count
            FROM control_verdicts
            WHERE tenant_id = :tenant_id
            GROUP BY regime
            """
        ),
        {"tenant_id": tenant_id},
    )
    regime_health = [dict(row) for row in regime_health_result.mappings().all()]

    unread_alerts_result = await db.execute(
        text("SELECT COUNT(*) FROM regulatory_alerts WHERE tenant_id = :tenant_id AND is_read = FALSE"),
        {"tenant_id": tenant_id},
    )
    unread_alerts = unread_alerts_result.scalar_one()

    return {
        "open_findings": int(open_row.get("open_total") or 0),
        "critical_findings": int(open_row.get("critical") or 0),
        "high_findings": int(open_row.get("high") or 0),
        "controls_passing": int(verdicts_row.get("passing") or 0),
        "controls_total": int(verdicts_row.get("total") or 0),
        "last_audit": dict(last_audit) if last_audit else None,
        "regime_health": regime_health,
        "unread_alerts": unread_alerts,
    }


# ─── Audit Log ───────────────────────────────────────────────────────────────

async def write_audit_log(
    db: AsyncSession,
    *,
    tenant_id: str | None,
    user_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
    changes: dict | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Bible Rule 3: audit_log is immutable — INSERT ONLY, no UPDATE or DELETE.
    """
    await db.execute(
        text(
            """
            INSERT INTO audit_log (
                tenant_id, user_id, action, resource_type, resource_id,
                ip_address, user_agent, request_id, changes, metadata
            ) VALUES (
                :tenant_id, :user_id, :action, :resource_type, :resource_id,
                CAST(:ip_address AS inet), :user_agent, :request_id, :changes, :metadata
            )
            """
        ),
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_id": request_id,
            "changes": __import__("json").dumps(changes) if changes else None,
            "metadata": __import__("json").dumps(metadata or {}),
        },
    )


# ─── Remediation ─────────────────────────────────────────────────────────────

async def get_remediation_dashboard(
    db: AsyncSession, *, tenant_id: str
) -> dict[str, Any]:
    """
    Return remediation items grouped by status bucket, plus summary counts.
    Frontend RemediationDashboard expects: tenant_id, actor_user_id, today,
    overdue, due_soon, in_progress, open, resolved, not_applicable arrays
    (each item matching RemediationItem type) and total_items,
    release_blocking_count, overdue_count.
    """
    # Fetch all remediation items for this tenant
    result = await db.execute(
        text(
            """
            SELECT r.id, r.finding_id, r.audit_id, r.tenant_id, r.title,
                   COALESCE(r.gap_note, '') AS gap_note,
                   COALESCE(f.severity, 'medium') AS severity,
                   r.status,
                   COALESCE(r.release_blocking, false) AS release_blocking,
                   r.assigned_to AS owner_user_id,
                   r.due_date, r.created_at, r.updated_at,
                CASE
                    WHEN r.status NOT IN ('resolved', 'not_applicable')
                         AND r.due_date IS NOT NULL
                         AND r.due_date < CURRENT_DATE THEN 'overdue'
                    WHEN r.status NOT IN ('resolved', 'not_applicable')
                         AND r.due_date IS NOT NULL
                         AND r.due_date >= CURRENT_DATE
                         AND r.due_date < CURRENT_DATE + INTERVAL '7 days' THEN 'due_soon'
                    ELSE r.status
                END AS bucket
            FROM remediation_items r
            LEFT JOIN findings f ON f.id = r.finding_id
            WHERE r.tenant_id = :tenant_id
            ORDER BY
                CASE COALESCE(f.severity, 'medium')
                    WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3 WHEN 'low' THEN 4
                    ELSE 5
                END,
                r.due_date ASC NULLS LAST
            """
        ),
        {"tenant_id": tenant_id},
    )
    rows = result.mappings().all()

    # Build item dicts matching frontend RemediationItem type
    item_keys = [
        "id", "finding_id", "audit_id", "tenant_id", "title", "gap_note",
        "severity", "status", "release_blocking", "owner_user_id",
        "due_date", "created_at", "updated_at",
    ]

    buckets: dict[str, list[dict[str, Any]]] = {
        "overdue": [],
        "due_soon": [],
        "in_progress": [],
        "open": [],
        "resolved": [],
        "not_applicable": [],
    }

    release_blocking_count = 0
    overdue_count = 0

    for row in rows:
        # Map to frontend RemediationItem shape
        item = {}
        for k in item_keys:
            val = row.get(k)
            item[k] = str(val) if val is not None and k in ("id", "finding_id", "audit_id", "tenant_id") else val
        # Frontend expects remediation_id not id
        item["remediation_id"] = item.pop("id")

        bucket = row["bucket"]

        if bucket == "overdue":
            buckets["overdue"].append(item)
            overdue_count += 1
        elif bucket == "due_soon":
            buckets["due_soon"].append(item)
        elif bucket in buckets:
            buckets[bucket].append(item)
        else:
            buckets["open"].append(item)

        # Release-blocking: critical/high severity items that are not resolved
        sev = (row.get("severity") or "medium").lower()
        if sev in ("critical", "high") and row["status"] not in (
            "resolved", "not_applicable"
        ):
            release_blocking_count += 1

    from datetime import date as date_type
    return {
        "tenant_id": tenant_id,
        "actor_user_id": "",
        "today": date_type.today().isoformat(),
        **buckets,
        "total_items": len(rows),
        "release_blocking_count": release_blocking_count,
        "overdue_count": overdue_count,
    }


async def list_remediation_items(
    db: AsyncSession, *, tenant_id: str
) -> list[dict[str, Any]]:
    result = await db.execute(
        text(
            """
            SELECT r.id, r.finding_id, r.audit_id, r.title, r.gap_note,
                   r.status, r.priority, r.assigned_to, r.due_date,
                   r.closed_at, r.notes, r.release_blocking,
                   r.created_at, r.updated_at,
                   COALESCE(f.severity, 'medium') AS severity,
                   f.control_id, f.control_name, f.regime,
                   f.finding AS finding_description
            FROM remediation_items r
            LEFT JOIN findings f ON f.id = r.finding_id
            WHERE r.tenant_id = :tenant_id
            ORDER BY
                CASE COALESCE(f.severity, 'medium')
                    WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3 WHEN 'low' THEN 4
                    ELSE 5
                END,
                r.due_date ASC NULLS LAST
            """
        ),
        {"tenant_id": tenant_id},
    )
    return [dict(row) for row in result.mappings().all()]
async def get_remediation_item(
    db: AsyncSession, *, item_id: str, tenant_id: str
) -> dict[str, Any] | None:
    result = await db.execute(
        text(
            """
            SELECT r.*, f.control_id, f.control_name, f.regime, f.finding AS finding_description
            FROM remediation_items r
            LEFT JOIN findings f ON f.id = r.finding_id
            WHERE r.id = :id AND r.tenant_id = :tenant_id
            """
        ),
        {"id": item_id, "tenant_id": tenant_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


# ─── Model Calls ─────────────────────────────────────────────────────────────

async def log_model_call(
    db: AsyncSession,
    *,
    tenant_id: str | None,
    audit_run_id: str | None,
    control_id: str | None,
    call_type: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int | None = None,
    timed_out: bool = False,
    error: str | None = None,
) -> str:
    """Log every AI model call per Bible Rule 6. Returns the model_call id."""
    call_id = str(uuid.uuid4())
    await db.execute(
        text(
            """
            INSERT INTO model_calls (
                id, tenant_id, audit_run_id, control_id, call_type, model,
                prompt_tokens, completion_tokens, total_tokens, latency_ms, timed_out, error
            ) VALUES (
                :id, :tenant_id, :audit_run_id, :control_id, :call_type, :model,
                :prompt_tokens, :completion_tokens, :total_tokens, :latency_ms, :timed_out, :error
            )
            """
        ),
        {
            "id": call_id,
            "tenant_id": tenant_id,
            "audit_run_id": audit_run_id,
            "control_id": control_id,
            "call_type": call_type,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "latency_ms": latency_ms,
            "timed_out": timed_out,
            "error": error,
        },
    )
    return call_id
