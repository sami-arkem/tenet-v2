from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import AuditExportOptions, Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.evidence_pack_service import (
    create_evidence_pack,
    execute_evidence_pack,
    get_evidence_pack,
    list_evidence_packs,
)


class EvidencePackCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    created_by: str
    manifest: dict[str, Any]


class EvidencePackListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: str
    name: str
    created_by: str
    created_at: str
    updated_at: str
    status: str
    manifest_summary: dict[str, Any]
    latest_execution: dict[str, Any] | None = None


class EvidencePackListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[EvidencePackListItem]


class EvidencePackDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: EvidencePackListItem
    manifest: dict[str, Any]


class EvidencePackExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    default_remediation_owner: str
    metadata: dict[str, Any] | None = None
    export: AuditExportOptions | None = None


class EvidencePackExecuteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: str
    pack_name: str
    execution: dict[str, Any]


router = APIRouter(prefix="/v1/evidence-packs", tags=["evidence-packs"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.get("", response_model=Envelope[EvidencePackListResponse])
def evidence_packs_list() -> Envelope[EvidencePackListResponse]:
    try:
        items = [EvidencePackListItem(**row) for row in list_evidence_packs()]
        return Envelope[EvidencePackListResponse](
            data=EvidencePackListResponse(items=items),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"evidence pack list failed: {exc}") from exc


@router.post("", response_model=Envelope[EvidencePackListItem])
def evidence_packs_create(request: EvidencePackCreateRequest) -> Envelope[EvidencePackListItem]:
    try:
        row = create_evidence_pack(
            name=request.name,
            created_by=request.created_by,
            manifest=request.manifest,
        )
        return Envelope[EvidencePackListItem](
            data=EvidencePackListItem(**row),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"evidence pack create failed: {exc}") from exc


@router.get("/{pack_id}", response_model=Envelope[EvidencePackDetailResponse])
def evidence_packs_get(pack_id: str) -> Envelope[EvidencePackDetailResponse]:
    try:
        row = get_evidence_pack(pack_id)
        return Envelope[EvidencePackDetailResponse](
            data=EvidencePackDetailResponse(
                detail=EvidencePackListItem(**row["detail"]),
                manifest=row["manifest"],
            ),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"evidence pack lookup failed: {exc}") from exc


@router.post("/{pack_id}/execute", response_model=Envelope[EvidencePackExecuteResponse])
def evidence_packs_execute(
    pack_id: str,
    request: EvidencePackExecuteRequest,
) -> Envelope[EvidencePackExecuteResponse]:
    try:
        row = execute_evidence_pack(
            pack_id=pack_id,
            run_id=request.run_id,
            default_remediation_owner=request.default_remediation_owner,
            metadata=request.metadata,
            export=request.export.model_dump() if request.export else None,
        )
        return Envelope[EvidencePackExecuteResponse](
            data=EvidencePackExecuteResponse(**row),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"evidence pack execution failed: {exc}") from exc
