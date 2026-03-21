from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import AuditExportOptions, Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.workflow_service import (
    WorkflowStateError,
    build_workflow_summary,
    create_workflow,
    execute_workflow_audit,
    list_workflows,
    refresh_workflow_readiness,
    refresh_workflow_remediation,
)


class WorkflowCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: str
    created_by: str


class WorkflowExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    default_remediation_owner: str
    metadata: dict[str, Any] | None = None
    export: AuditExportOptions | None = None


class WorkflowSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    pack_id: str
    pack_name: str
    company_name: str
    audit_type: str
    domain: str
    jurisdictions: list[str]
    status: str
    latest_readiness: dict[str, Any] | None = None
    latest_execution: dict[str, Any] | None = None
    latest_remediation_summary: dict[str, Any] | None = None
    timeline: list[dict[str, Any]]
    created_at: str
    updated_at: str


class WorkflowListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[WorkflowSummaryResponse]


router = APIRouter(prefix="/v1/workflows", tags=["workflows"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.get("", response_model=Envelope[WorkflowListResponse])
def workflows_list() -> Envelope[WorkflowListResponse]:
    try:
        rows = [WorkflowSummaryResponse(**build_workflow_summary(row["workflow_id"])) for row in list_workflows()]
        return Envelope[WorkflowListResponse](
            data=WorkflowListResponse(items=rows),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"workflow list failed: {exc}") from exc


@router.post("", response_model=Envelope[WorkflowSummaryResponse])
def workflows_create(request: WorkflowCreateRequest) -> Envelope[WorkflowSummaryResponse]:
    try:
        row = create_workflow(
            pack_id=request.pack_id,
            created_by=request.created_by,
        )
        return Envelope[WorkflowSummaryResponse](
            data=WorkflowSummaryResponse(**build_workflow_summary(row["workflow_id"])),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"workflow create failed: {exc}") from exc


@router.get("/{workflow_id}", response_model=Envelope[WorkflowSummaryResponse])
def workflows_get(workflow_id: str) -> Envelope[WorkflowSummaryResponse]:
    try:
        row = build_workflow_summary(workflow_id)
        return Envelope[WorkflowSummaryResponse](
            data=WorkflowSummaryResponse(**row),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"workflow lookup failed: {exc}") from exc


@router.post("/{workflow_id}/readiness", response_model=Envelope[WorkflowSummaryResponse])
def workflows_refresh_readiness(workflow_id: str) -> Envelope[WorkflowSummaryResponse]:
    try:
        row = refresh_workflow_readiness(workflow_id)
        return Envelope[WorkflowSummaryResponse](
            data=WorkflowSummaryResponse(**build_workflow_summary(row["workflow_id"])),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"workflow readiness refresh failed: {exc}") from exc


@router.post("/{workflow_id}/execute", response_model=Envelope[WorkflowSummaryResponse])
def workflows_execute(
    workflow_id: str,
    request: WorkflowExecuteRequest,
) -> Envelope[WorkflowSummaryResponse]:
    try:
        row = execute_workflow_audit(
            workflow_id=workflow_id,
            run_id=request.run_id,
            default_remediation_owner=request.default_remediation_owner,
            metadata=request.metadata,
            export=request.export.model_dump() if request.export else None,
        )
        return Envelope[WorkflowSummaryResponse](
            data=WorkflowSummaryResponse(**build_workflow_summary(row["workflow_id"])),
            meta=build_meta(),
            error=None,
        )
    except WorkflowStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"workflow execute failed: {exc}") from exc


@router.post("/{workflow_id}/remediation", response_model=Envelope[WorkflowSummaryResponse])
def workflows_refresh_remediation(workflow_id: str) -> Envelope[WorkflowSummaryResponse]:
    try:
        row = refresh_workflow_remediation(workflow_id)
        return Envelope[WorkflowSummaryResponse](
            data=WorkflowSummaryResponse(**build_workflow_summary(row["workflow_id"])),
            meta=build_meta(),
            error=None,
        )
    except WorkflowStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"workflow remediation refresh failed: {exc}") from exc
