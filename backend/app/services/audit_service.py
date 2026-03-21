"""
Audit service — orchestrates the AuditAgent with DB persistence.
Called by background jobs (or directly from the audits router for synchronous mode).
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.audit_agent import AuditAgent, AuditResult, ControlDefinition, EvidenceItem
from app.db.connection import set_tenant_context
from app.db.queries import (
    insert_findings_from_verdicts,
    log_model_call,
    update_audit_run_status,
    write_audit_log,
)

logger = logging.getLogger("tenet.audit_service")

_agent = AuditAgent()


async def execute_audit(
    db: AsyncSession,
    *,
    run_id: str,
    tenant_id: str,
    jurisdiction: str,
    regime_scope: list[str],
    company_profile: dict[str, Any],
    entity_id: str | None = None,
) -> AuditResult:
    """
    Full audit execution pipeline:
    1. Load evidence from DB
    2. Load applicable controls from gold case library
    3. Run AuditAgent
    4. Persist verdicts and findings
    5. Update audit_run status
    6. Write audit log entry
    """
    await set_tenant_context(db, tenant_id)

    # Mark as RUNNING
    await update_audit_run_status(db, run_id=run_id, tenant_id=tenant_id, status="RUNNING")

    try:
        # Load evidence
        evidence = await _load_evidence(db, run_id=run_id, tenant_id=tenant_id)

        # Load controls for this jurisdiction + regime
        controls = _load_controls(jurisdiction=jurisdiction, regime_scope=regime_scope)

        async def _log_call(**kwargs: Any) -> str:
            return await log_model_call(db, **kwargs)

        # Run the audit engine
        result = await _agent.run_audit(
            run_id=run_id,
            tenant_id=tenant_id,
            jurisdiction=jurisdiction,
            regime_scope=regime_scope,
            company_profile=company_profile,
            evidence_items=evidence,
            controls=controls,
            model_call_logger=_log_call,
        )

        # Persist control verdicts
        verdict_rows = [
            {
                "id": None,
                "control_id": v.control_id,
                "control_name": v.control_name,
                "regime": v.regime,
                "jurisdiction": v.jurisdiction,
                "verdict": v.verdict,
                "severity": v.severity,
                "reason_code": v.reason_code,
                "finding": v.finding,
                "requirement": v.requirement,
                "gap": v.gap,
                "risk": v.risk,
                "recommended_action": v.recommended_action,
                "regulatory_reference": v.regulatory_reference,
                "evidence_ids": v.evidence_ids,
            }
            for v in result.verdicts
        ]

        # Persist findings (non-PASS verdicts)
        await insert_findings_from_verdicts(
            db,
            tenant_id=tenant_id,
            audit_run_id=run_id,
            entity_id=entity_id,
            verdicts=verdict_rows,
        )

        # Update audit run with final counts
        await update_audit_run_status(
            db,
            run_id=run_id,
            tenant_id=tenant_id,
            status="COMPLETE",
            overall_verdict=result.overall_verdict,
            posture=result.posture,
            control_count=len(result.verdicts),
            pass_count=result.pass_count,
            partial_count=result.partial_count,
            fail_count=result.fail_count,
            missing_count=result.missing_count,
            na_count=result.na_count,
        )

        await write_audit_log(
            db,
            tenant_id=tenant_id,
            user_id=None,
            action="AUDIT_COMPLETED",
            resource_type="audit_run",
            resource_id=run_id,
            metadata={
                "verdict": result.overall_verdict,
                "posture": result.posture,
                "controls": len(result.verdicts),
            },
        )

        logger.info(
            "Audit %s completed: verdict=%s posture=%s controls=%d",
            run_id, result.overall_verdict, result.posture, len(result.verdicts),
        )
        return result

    except Exception as exc:
        logger.exception("Audit %s failed: %s", run_id, exc)
        await update_audit_run_status(
            db, run_id=run_id, tenant_id=tenant_id, status="FAILED", error_message=str(exc)
        )
        await write_audit_log(
            db,
            tenant_id=tenant_id,
            user_id=None,
            action="AUDIT_FAILED",
            resource_type="audit_run",
            resource_id=run_id,
            metadata={"error": str(exc)},
        )
        raise


async def _load_evidence(
    db: AsyncSession, *, run_id: str, tenant_id: str
) -> list[EvidenceItem]:
    """Load READY evidence items associated with this audit run."""
    from sqlalchemy import text

    result = await db.execute(
        text(
            """
            SELECT id, document_type, original_name, extracted_text, file_hash
            FROM evidence_items
            WHERE audit_run_id = :run_id
              AND tenant_id = :tenant_id
              AND status = 'READY'
            """
        ),
        {"run_id": run_id, "tenant_id": tenant_id},
    )
    return [
        EvidenceItem(
            id=str(row["id"]),
            category=row["document_type"] or "UNKNOWN",
            filename=row["original_name"],
            extracted_text=row["extracted_text"] or "",
            file_hash=row["file_hash"],
        )
        for row in result.mappings().all()
    ]


def _load_controls(
    *, jurisdiction: str, regime_scope: list[str]
) -> list[ControlDefinition]:
    """
    Load controls from the Gold Case Control Registry (Bible §11).
    Uses control_registry.py as the single source of truth.
    """
    from app.agents.control_registry import get_controls_for_regimes

    registry_controls = get_controls_for_regimes(regime_scope)

    return [
        ControlDefinition(
            control_id=ctrl.control_id,
            control_name=ctrl.name,
            regime=ctrl.regime.value,
            jurisdiction=jurisdiction,
            severity=ctrl.severity.value,
            required_evidence_categories=ctrl.required_evidence_types,
            regulatory_reference=ctrl.regulatory_reference,
            requirement=ctrl.description,
            evaluation_criteria=",".join(ctrl.scoring_keywords),
        )
        for ctrl in registry_controls
    ]
