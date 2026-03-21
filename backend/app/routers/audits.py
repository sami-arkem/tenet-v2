"""
Audits router — Bible §4.4.
Every endpoint: auth required, tenant isolation enforced at DB level.
"""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, set_tenant_context
from app.db.connection import AsyncSessionLocal
from app.db.queries import (
    create_audit_run,
    get_audit_run,
    get_running_audit,
    insert_findings_from_verdicts,
    list_audit_runs,
    update_audit_run_status,
    write_audit_log,
)
from app.schemas.audit import AuditListResponse, AuditSummaryResponse, CreateAuditRequest
from app.schemas.response import ApiResponse

router = APIRouter()
logger = logging.getLogger("tenet.audits")


# ─── Framework → Regime mapping ───────────────────────────────────────────────

def _framework_to_regimes(framework: str, jurisdiction: str) -> list[str]:
    """Map audit framework/jurisdiction to control regime_scope."""
    fw = (framework or "").upper().strip()
    jur = (jurisdiction or "").upper().strip()

    # Direct framework → regimes
    FRAMEWORK_MAP: dict[str, list[str]] = {
        "FCA": ["AML", "GDPR", "FCA", "SANCTIONS"],
        "MAS": ["AML", "GDPR", "SANCTIONS"],
        "DFSA": ["AML", "SANCTIONS"],
        "ADGM": ["AML", "SANCTIONS"],
        "GDPR": ["GDPR"],
        "AML": ["AML", "SANCTIONS"],
        "FINCEN": ["AML", "SANCTIONS"],
        "SEC": ["AML", "SANCTIONS"],
        "FINRA": ["AML", "SANCTIONS"],
        "AUSTRAC": ["AML", "SANCTIONS"],
        "ASIC": ["AML", "SANCTIONS"],
        "FINTRAC": ["AML", "SANCTIONS"],
        "OSFI": ["AML", "GDPR", "SANCTIONS"],
        "SANCTIONS": ["SANCTIONS"],
        "AML_KYC": ["AML", "SANCTIONS"],
        "AML_PERIODIC": ["AML", "SANCTIONS"],
        "KYC_PERIODIC": ["AML"],
        "SANCTIONS_SCREENING": ["SANCTIONS"],
        "GOVERNANCE_REVIEW": ["AML", "GDPR", "FCA"],
        "FRAUD_CONTROLS": ["AML", "SANCTIONS"],
        "VENDOR_RISK": ["AML", "GDPR"],
    }

    # Check direct match
    if fw in FRAMEWORK_MAP:
        return FRAMEWORK_MAP[fw]

    # Partial match
    for key, regimes in FRAMEWORK_MAP.items():
        if key in fw or fw in key:
            return regimes

    # Jurisdiction fallback
    JURISDICTION_MAP: dict[str, list[str]] = {
        "UK": ["AML", "GDPR", "FCA", "SANCTIONS"],
        "GB": ["AML", "GDPR", "FCA", "SANCTIONS"],
        "EU": ["AML", "GDPR", "SANCTIONS"],
        "US": ["AML", "SANCTIONS"],
        "SG": ["AML", "GDPR", "SANCTIONS"],
        "AE": ["AML", "SANCTIONS"],
        "UAE": ["AML", "SANCTIONS"],
        "AU": ["AML", "SANCTIONS"],
        "CA": ["AML", "GDPR", "SANCTIONS"],
        "HK": ["AML", "SANCTIONS"],
        "IN": ["AML", "SANCTIONS"],
    }
    if jur in JURISDICTION_MAP:
        return JURISDICTION_MAP[jur]

    return ["AML", "GDPR", "SANCTIONS"]


# ─── Background audit runner ──────────────────────────────────────────────────

async def _run_audit_background(
    run_id: str,
    tenant_id: str,
    entity_id: str | None,
    framework: str,
    jurisdiction: str,
    regime_scope: list[str],
    company_profile_raw: str,
    evidence_ids: list[str],
) -> None:
    """
    Background task: execute the full compliance audit pipeline.
    Bible Rule 1: verdicts are 100% deterministic Python.
    Bible Rule 6: every model call is logged.
    """
    from app.agents.audit_agent import AuditAgent, ControlDefinition, EvidenceItem
    from app.agents.control_registry import get_controls_for_regimes
    from app.db.queries import log_model_call

    logger.info("Audit %s: background runner started", run_id)

    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, tenant_id)
        try:
            # ── 1. Load evidence items from DB ────────────────────────────────
            ev_result = await db.execute(
                text("""
                    SELECT id, COALESCE(document_type, 'UNKNOWN') as document_type, COALESCE(original_name, file_name) as original_name, COALESCE(ocr_text, '') as extracted_text, file_hash
                    FROM evidence_items
                    WHERE (audit_run_id = :run_id OR id = ANY(:ev_ids))
                      AND tenant_id = :tenant_id
                      AND status IN ('READY', 'PROCESSING', 'EMPTY')
                """),
                {
                    "run_id": run_id,
                    "tenant_id": tenant_id,
                    "ev_ids": evidence_ids if evidence_ids else [],
                },
            )
            ev_rows = ev_result.mappings().all()
            evidence_items = [
                EvidenceItem(
                    id=str(row["id"]),
                    category=str(row["document_type"] or "UNKNOWN"),
                    filename=str(row["original_name"] or ""),
                    extracted_text=str(row["extracted_text"] or ""),
                    file_hash=str(row["file_hash"] or ""),
                )
                for row in ev_rows
            ]
            logger.info("Audit %s: loaded %d evidence items", run_id, len(evidence_items))

            # ── 2. Resolve regime_scope → controls ────────────────────────────
            if not regime_scope:
                regime_scope = _framework_to_regimes(framework, jurisdiction)

            registry_controls = get_controls_for_regimes(regime_scope)

            # If still empty, try framework as regime directly
            if not registry_controls:
                registry_controls = get_controls_for_regimes([framework.upper()])

            controls = [
                ControlDefinition(
                    control_id=c.control_id,
                    control_name=c.name,
                    regime=c.regime.value if hasattr(c.regime, "value") else str(c.regime),
                    jurisdiction=jurisdiction or "GLOBAL",
                    severity=c.severity.value if hasattr(c.severity, "value") else str(c.severity),
                    required_evidence_categories=list(c.required_evidence_types),
                    regulatory_reference=c.regulatory_reference,
                    requirement=c.description,
                    evaluation_criteria=", ".join(c.scoring_keywords),
                )
                for c in registry_controls
            ]

            # Fallback generic controls if none found
            if not controls:
                controls = _generic_fallback_controls(jurisdiction, framework)

            logger.info("Audit %s: loaded %d controls for regimes %s", run_id, len(controls), regime_scope)

            # ── 3. Parse company profile ──────────────────────────────────────
            profile: dict = {}
            try:
                if isinstance(company_profile_raw, str) and company_profile_raw.strip():
                    profile = json.loads(company_profile_raw)
                elif isinstance(company_profile_raw, dict):
                    profile = company_profile_raw
            except Exception:
                pass

            # ── 4. Run the audit agent ────────────────────────────────────────
            agent = AuditAgent()

            async def model_call_logger(**kwargs):  # type: ignore[return]
                return await log_model_call(db, **kwargs)

            audit_result = await agent.run_audit(
                run_id=run_id,
                tenant_id=tenant_id,
                jurisdiction=jurisdiction,
                regime_scope=regime_scope,
                company_profile=profile,
                evidence_items=evidence_items,
                controls=controls,
                model_call_logger=model_call_logger,
            )
            logger.info(
                "Audit %s: complete — %s/%s/%s PASS/PARTIAL/FAIL, verdict=%s",
                run_id, audit_result.pass_count, audit_result.partial_count,
                audit_result.fail_count, audit_result.overall_verdict,
            )

            # ── 5. Persist control verdicts to DB ─────────────────────────────
            for v in audit_result.verdicts:
                try:
                    await db.execute(
                        text("""
                            INSERT INTO control_verdicts (
                                tenant_id, audit_run_id,
                                control_id, control_name, regime, jurisdiction,
                                verdict, severity, finding, requirement,
                                gap, risk,
                                recommended_action, regulatory_reference
                            ) VALUES (
                                :tenant_id, :audit_run_id,
                                :control_id, :control_name, :regime, :jurisdiction,
                                :verdict, :severity, :finding, :requirement,
                                :gap, :risk,
                                :recommended_action, :regulatory_reference
                            ) ON CONFLICT DO NOTHING
                        """),
                        {
                            "tenant_id": tenant_id,
                            "audit_run_id": run_id,
                            "control_id": v.control_id,
                            "control_name": v.control_name,
                            "regime": v.regime,
                            "jurisdiction": v.jurisdiction,
                            "verdict": v.verdict,
                            "severity": v.severity,
                            "finding": v.finding,
                            "requirement": v.requirement,
                            "gap": v.gap,
                            "risk": v.risk,
                            "recommended_action": v.recommended_action,
                            "regulatory_reference": v.regulatory_reference,
                        },
                    )
                except Exception as exc:
                    logger.warning("Failed to insert control verdict %s: %s", v.control_id, exc)

            # ── 6. Insert findings from verdicts ──────────────────────────────
            verdict_dicts = [
                {
                    "control_id": v.control_id,
                    "control_name": v.control_name,
                    "regime": v.regime,
                    "jurisdiction": v.jurisdiction,
                    "verdict": v.verdict,
                    "severity": v.severity,
                    "finding": v.finding,
                    "requirement": v.requirement,
                    "gap": v.gap,
                    "risk": v.risk,
                    "recommended_action": v.recommended_action,
                    "regulatory_reference": v.regulatory_reference,
                }
                for v in audit_result.verdicts
            ]
            try:
                await insert_findings_from_verdicts(
                    db,
                    tenant_id=tenant_id,
                    audit_run_id=run_id,
                    entity_id=entity_id,
                    verdicts=verdict_dicts,
                )
            except Exception as exc:
                logger.warning("Findings insert error: %s", exc)

            # ── 7. Determine final status & deployment decision ────────────────
            critical_fails = sum(
                1 for v in audit_result.verdicts
                if v.verdict in ("FAIL", "MISSING_EVIDENCE") and v.severity == "CRITICAL"
            )
            ov = audit_result.overall_verdict or "FAIL"

            if ov == "PASS":
                final_status = "COMPLETE"
                deployment_decision = "APPROVED"
                release_ready = True
            elif critical_fails > 0:
                final_status = "COMPLETE"
                deployment_decision = "BLOCKED"
                release_ready = False
            elif ov == "PARTIAL" or audit_result.fail_count > 0:
                final_status = "COMPLETE"
                deployment_decision = "CONDITIONAL"
                release_ready = False
            else:
                final_status = "COMPLETE"
                deployment_decision = "APPROVED"
                release_ready = True

            await update_audit_run_status(
                db,
                run_id=run_id,
                tenant_id=tenant_id,
                status=final_status,
                overall_verdict=ov,
                posture=audit_result.posture,
                pass_count=audit_result.pass_count,
                partial_count=audit_result.partial_count,
                fail_count=audit_result.fail_count,
                missing_count=audit_result.missing_count,
                na_count=audit_result.na_count,
                control_count=len(audit_result.verdicts),
            )

            # Update deployment_decision and release_ready
            await db.execute(
                text("""
                    UPDATE audit_runs
                    SET deployment_decision = :decision,
                        release_ready = :release_ready,
                        updated_at = NOW()
                    WHERE id = :run_id AND tenant_id = :tenant_id
                """),
                {
                    "decision": deployment_decision,
                    "release_ready": release_ready,
                    "run_id": run_id,
                    "tenant_id": tenant_id,
                },
            )

            await db.commit()
            logger.info("Audit %s: completed with status=%s decision=%s", run_id, final_status, deployment_decision)

        except Exception as exc:
            logger.exception("Audit %s: background runner failed: %s", run_id, exc)
            try:
                await update_audit_run_status(
                    db,
                    run_id=run_id,
                    tenant_id=tenant_id,
                    status="FAILED",
                    error_message=str(exc)[:500],
                )
                await db.commit()
            except Exception as inner:
                logger.error("Audit %s: failed to write FAILED status: %s", run_id, inner)


def _generic_fallback_controls(jurisdiction: str, framework: str) -> list:
    """Fallback generic controls when no specific controls match the regime_scope."""
    from app.agents.audit_agent import ControlDefinition
    return [
        ControlDefinition(
            control_id="GEN-01",
            control_name="Compliance Programme — Written Policies",
            regime="GENERIC",
            jurisdiction=jurisdiction or "GLOBAL",
            severity="HIGH",
            required_evidence_categories=["AML_POLICY", "RISK_ASSESSMENT"],
            regulatory_reference=f"{framework or 'Applicable'} compliance requirements",
            requirement="The firm must maintain documented compliance policies and procedures.",
            evaluation_criteria="compliance, policy, procedure, programme, written, documented, framework",
        ),
        ControlDefinition(
            control_id="GEN-02",
            control_name="Risk Assessment — Enterprise Risk Framework",
            regime="GENERIC",
            jurisdiction=jurisdiction or "GLOBAL",
            severity="HIGH",
            required_evidence_categories=["RISK_ASSESSMENT"],
            regulatory_reference=f"{framework or 'Applicable'} risk management requirements",
            requirement="The firm must conduct and document enterprise risk assessments.",
            evaluation_criteria="risk assessment, risk management, risk framework, risk appetite, inherent risk, residual risk, risk register",
        ),
        ControlDefinition(
            control_id="GEN-03",
            control_name="Staff Training — Compliance Training Records",
            regime="GENERIC",
            jurisdiction=jurisdiction or "GLOBAL",
            severity="MEDIUM",
            required_evidence_categories=["TRAINING_RECORDS"],
            regulatory_reference=f"{framework or 'Applicable'} training requirements",
            requirement="Staff must receive compliance training appropriate to their role annually.",
            evaluation_criteria="training, staff training, compliance training, training records, training certificate, annual training, e-learning",
        ),
        ControlDefinition(
            control_id="GEN-04",
            control_name="Governance — Board Oversight and Minutes",
            regime="GENERIC",
            jurisdiction=jurisdiction or "GLOBAL",
            severity="MEDIUM",
            required_evidence_categories=["BOARD_MINUTES"],
            regulatory_reference=f"{framework or 'Applicable'} governance requirements",
            requirement="The firm must document board-level oversight of compliance matters.",
            evaluation_criteria="board minutes, board meeting, governance, oversight, director, committee, resolution, compliance oversight",
        ),
    ]


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ApiResponse[AuditSummaryResponse],
    status_code=201,
    summary="Start a new audit run",
)
async def create_audit(
    request: Request,
    body: CreateAuditRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AuditSummaryResponse]:
    tenant_id: str = request.state.tenant_id
    user_id: str = request.state.user_id
    await set_tenant_context(db, tenant_id)

    if not body.force:
        existing = await get_running_audit(db, tenant_id=tenant_id, entity_id=body.entity_id or None)
        if existing:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "AUDIT_IN_PROGRESS",
                    "message": f"An audit is already running (run_id: {existing['id']})",
                },
            )

    run = await create_audit_run(
        db,
        tenant_id=tenant_id,
        entity_id=body.entity_id or None,
        system_name=body.system_name,
        audit_kind=body.audit_kind,
        framework=body.framework,
        jurisdiction=body.jurisdiction,
        regime_scope=body.regime_scope or [body.framework],
        company_profile=body.company_profile or {},
        evidence_ids=body.evidence_ids or [],
        started_by=user_id,
        note=body.note,
    )

    await write_audit_log(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="AUDIT_CREATED",
        resource_type="audit_run",
        resource_id=str(run["id"]),
        request_id=getattr(request.state, "request_id", None),
    )

    return ApiResponse.success(
        data=_to_response(run),
        request_id=getattr(request.state, "request_id", None),
        run_id=str(run["id"]),
    )


@router.get(
    "",
    response_model=ApiResponse[AuditListResponse],
    summary="List audit runs for this tenant",
)
async def list_audits(
    request: Request,
    entity_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AuditListResponse]:
    tenant_id: str = request.state.tenant_id
    await set_tenant_context(db, tenant_id)
    if limit > 100:
        limit = 100

    result = await list_audit_runs(
        db, tenant_id=tenant_id, entity_id=entity_id, status=status, limit=limit, offset=offset
    )

    return ApiResponse.success(
        data=AuditListResponse(
            items=[_to_response(r) for r in result["items"]],
            total=result["total"],
            limit=limit,
            offset=offset,
        ),
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/{run_id}",
    response_model=ApiResponse[AuditSummaryResponse],
    summary="Get audit run detail",
)
async def get_audit(
    run_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AuditSummaryResponse]:
    tenant_id: str = request.state.tenant_id
    await set_tenant_context(db, tenant_id)

    run = await get_audit_run(db, run_id=run_id, tenant_id=tenant_id)
    if not run:
        raise HTTPException(
            status_code=404,
            detail={"code": "AUDIT_NOT_FOUND", "message": "Audit run not found"},
        )

    return ApiResponse.success(
        data=_to_response(run),
        request_id=getattr(request.state, "request_id", None),
        run_id=run_id,
    )


@router.get("/{audit_id}/runs/latest", summary="Get latest run for an audit")
async def get_latest_run(
    audit_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    tenant_id: str = request.state.tenant_id
    await set_tenant_context(db, tenant_id)

    run = await get_audit_run(db, run_id=audit_id, tenant_id=tenant_id)
    if not run:
        raise HTTPException(
            status_code=404,
            detail={"code": "AUDIT_NOT_FOUND", "message": "Audit run not found"},
        )

    status = (run.get("status") or "CREATED").upper()
    if status == "COMPLETE":
        status = "COMPLETED"

    return ApiResponse.success(
        data={
            "run_id": str(run["id"]),
            "audit_id": str(run["id"]),
            "tenant_id": str(run["tenant_id"]),
            "status": status,
            "deployment_decision": run.get("deployment_decision") or "UNKNOWN",
            "report_ready": status in ("COMPLETED", "COMPLETE"),
            "export_ready": status in ("COMPLETED", "COMPLETE"),
            "finalization_ready": status in ("COMPLETED", "COMPLETE"),
            "started_at": str(run.get("started_at")) if run.get("started_at") else None,
            "completed_at": str(run.get("completed_at")) if run.get("completed_at") else None,
        },
        request_id=getattr(request.state, "request_id", None),
    ).model_dump(mode="json")


@router.get("/{audit_id}/preparation", summary="Get audit preparation status")
async def get_audit_preparation(
    audit_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Return preparation status for an audit run.
    READY when audit is in CREATED state (ready to run).
    NOT_READY when already RUNNING or COMPLETE.
    """
    tenant_id: str = request.state.tenant_id
    await set_tenant_context(db, tenant_id)

    run = await get_audit_run(db, run_id=audit_id, tenant_id=tenant_id)
    if not run:
        raise HTTPException(
            status_code=404,
            detail={"code": "AUDIT_NOT_FOUND", "message": "Audit not found"},
        )

    status = (run.get("status") or "CREATED").upper()

    # Count uploaded evidence
    ev_result = await db.execute(
        text("SELECT COUNT(*) FROM evidence_items WHERE audit_run_id = :run_id AND tenant_id = :tenant_id AND status != 'DELETED'"),
        {"run_id": audit_id, "tenant_id": tenant_id},
    )
    evidence_count = ev_result.scalar_one() or 0

    if status == "RUNNING":
        prep_status = "NOT_READY"
        blocking = ["Audit is currently running"]
    elif status in ("COMPLETE", "COMPLETED"):
        prep_status = "NOT_READY"
        blocking = ["Audit has already completed"]
    else:
        prep_status = "READY"
        blocking = []

    return ApiResponse.success(
        data={
            "audit_id": audit_id,
            "preparation_status": prep_status,
            "blocking_reasons": blocking,
            "evidence_count": evidence_count,
            "checklist": [],
        }
    ).model_dump(mode="json")


@router.post("/{audit_id}/run", summary="Trigger an audit run (async execution)")
async def trigger_audit_run(
    audit_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Trigger execution of a compliance audit.
    Sets status RUNNING immediately, then runs the full pipeline in background.
    Bible Rule 1: verdicts are deterministic Python. Model only for narrative.
    """
    tenant_id: str = request.state.tenant_id
    user_id: str = request.state.user_id
    await set_tenant_context(db, tenant_id)

    run = await get_audit_run(db, run_id=audit_id, tenant_id=tenant_id)
    if not run:
        raise HTTPException(
            status_code=404,
            detail={"code": "AUDIT_NOT_FOUND", "message": "Audit run not found"},
        )

    current_status = (run.get("status") or "").upper()
    if current_status == "RUNNING":
        raise HTTPException(
            status_code=409,
            detail={"code": "AUDIT_IN_PROGRESS", "message": "Audit is already running"},
        )

    # Set RUNNING immediately so UI updates fast
    await update_audit_run_status(
        db, run_id=audit_id, tenant_id=tenant_id, status="RUNNING"
    )
    await db.commit()

    await write_audit_log(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="AUDIT_RUN_TRIGGERED",
        resource_type="audit_run",
        resource_id=audit_id,
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()

    # Parse regime_scope (stored as comma-sep TEXT in DB)
    regime_scope_raw = run.get("regime_scope") or ""
    if isinstance(regime_scope_raw, list):
        regime_scope = [r.strip() for r in regime_scope_raw if r and r.strip()]
    elif isinstance(regime_scope_raw, str):
        regime_scope = [r.strip() for r in regime_scope_raw.split(",") if r.strip()]
    else:
        regime_scope = []

    # Parse evidence_ids
    evidence_ids_raw = run.get("evidence_ids") or []
    evidence_ids = [str(e) for e in evidence_ids_raw] if evidence_ids_raw else []

    # Kick off background audit execution
    background_tasks.add_task(
        _run_audit_background,
        run_id=audit_id,
        tenant_id=tenant_id,
        entity_id=str(run["entity_id"]) if run.get("entity_id") else None,
        framework=run.get("framework") or "",
        jurisdiction=run.get("jurisdiction") or "",
        regime_scope=regime_scope,
        company_profile_raw=run.get("company_profile") or "{}",
        evidence_ids=evidence_ids,
    )

    return ApiResponse.success(
        data={
            "audit_id": audit_id,
            "run_id": audit_id,
            "queue_status": "started",
            "message": "Audit execution started. Poll GET /v1/audits/{audit_id} for status.",
        },
        request_id=getattr(request.state, "request_id", None),
    ).model_dump(mode="json")


def _to_response(row: dict) -> AuditSummaryResponse:
    """Map DB row to frontend AuditSummary shape."""
    status = (row.get("status") or "CREATED").upper()
    if status == "PENDING":
        status = "CREATED"
    if status == "COMPLETE":
        status = "COMPLETED"

    return AuditSummaryResponse(
        audit_id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        audit_kind=row.get("audit_kind") or "compliance_audit",
        entity_id=str(row["entity_id"]) if row.get("entity_id") else None,
        system_name=row.get("system_name") or "Untitled System",
        jurisdiction=row.get("jurisdiction") or "",
        framework=row.get("framework") or row.get("jurisdiction") or "",
        status=status,
        deployment_decision=row.get("deployment_decision") or "UNKNOWN",
        release_ready=bool(row.get("release_ready")),
        created_at=row.get("created_at") or row.get("started_at"),
        updated_at=row.get("updated_at") or row.get("created_at") or row.get("started_at"),
        overall_verdict=row.get("overall_verdict"),
        posture=row.get("posture"),
        control_count=row.get("control_count") or 0,
        pass_count=row.get("pass_count") or 0,
        partial_count=row.get("partial_count") or 0,
        fail_count=row.get("fail_count") or 0,
        missing_count=row.get("missing_count") or 0,
        na_count=row.get("na_count") or 0,
        latest_run_id=str(row["id"]),
        note=row.get("note"),
    )
