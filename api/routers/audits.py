from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import (
    AuditCreateRequest,
    AuditCreateResponse,
    AuditDetailResponse,
    AuditListItem,
    AuditListResponse,
    Envelope,
    MetaBody,
    ReportResponse,
)
from api.store import execute_and_store_audit, get_audit_detail, list_audits, new_request_id, utc_now_iso


router = APIRouter(prefix="/v1/audits", tags=["audits"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.get("", response_model=Envelope[AuditListResponse])
def audits_list() -> Envelope[AuditListResponse]:
    items = [AuditListItem(**row) for row in list_audits()]
    return Envelope[AuditListResponse](
        data=AuditListResponse(items=items),
        meta=build_meta(),
        error=None,
    )


@router.post("", response_model=Envelope[AuditCreateResponse])
def audits_create(request: AuditCreateRequest) -> Envelope[AuditCreateResponse]:
    try:
        detail = execute_and_store_audit(
            payload=request.payload,
            export=request.export.model_dump() if request.export else None,
        )
        response = AuditCreateResponse(
            run_id=detail["run_id"],
            status=detail["deterministic_audit_result"]["status"],
            snapshot=detail["snapshot"],
            topline=detail["topline"],
            export_package=detail.get("export_package"),
        )
        return Envelope[AuditCreateResponse](
            data=response,
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"audit creation failed: {exc}") from exc


@router.get("/{run_id}", response_model=Envelope[AuditDetailResponse])
def audits_get(run_id: str) -> Envelope[AuditDetailResponse]:
    try:
        detail = get_audit_detail(run_id)
        response = AuditDetailResponse(
            run_id=detail["run_id"],
            deterministic_audit_result=detail["deterministic_audit_result"],
            report_pack=detail["report_pack"],
            report_bundle=detail["report_bundle"],
            snapshot=detail["snapshot"],
            topline=detail["topline"],
            export_package=detail.get("export_package"),
        )
        return Envelope[AuditDetailResponse](
            data=response,
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"audit lookup failed: {exc}") from exc


@router.get("/{run_id}/report", response_model=Envelope[ReportResponse])
def audits_report(run_id: str) -> Envelope[ReportResponse]:
    try:
        detail = get_audit_detail(run_id)
        report_bundle = detail["report_bundle"]
        response = ReportResponse(
            run_id=detail["run_id"],
            markdown=report_bundle["markdown"],
            deployment_decision=report_bundle["deployment_decision"],
            overall_posture=report_bundle["overall_posture"],
            finding_count=report_bundle["finding_count"],
            remediation_count=report_bundle["remediation_count"],
        )
        return Envelope[ReportResponse](
            data=response,
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"report lookup failed: {exc}") from exc
