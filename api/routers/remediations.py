from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.remediation_service import (
    build_remediation_summary,
    get_remediation,
    update_remediation,
)


class RemediationItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    remediation_id: str
    finding_id: str
    title: str
    owner: str
    due_date: str | None = None
    status: str
    action_required: str
    evidence_links: list[str] = Field(default_factory=list)
    comment_history: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
    status_source: str | None = None


class RemediationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    item_count: int
    status_counts: dict[str, int]
    items: list[RemediationItemResponse]


class RemediationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner: str | None = None
    due_date: str | None = None
    status: str | None = None
    action_required: str | None = None
    note: str | None = None
    evidence_links: list[str] | None = None


router = APIRouter(prefix="/v1/audits/{run_id}/remediations", tags=["remediations"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.get("", response_model=Envelope[RemediationListResponse])
def remediations_list(run_id: str) -> Envelope[RemediationListResponse]:
    try:
        summary = build_remediation_summary(run_id)
        response = RemediationListResponse(
            run_id=summary["run_id"],
            item_count=summary["item_count"],
            status_counts=summary["status_counts"],
            items=[RemediationItemResponse(**row) for row in summary["items"]],
        )
        return Envelope[RemediationListResponse](
            data=response,
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"remediation list failed: {exc}") from exc


@router.get("/{remediation_id}", response_model=Envelope[RemediationItemResponse])
def remediations_get(run_id: str, remediation_id: str) -> Envelope[RemediationItemResponse]:
    try:
        row = get_remediation(run_id, remediation_id)
        response = RemediationItemResponse(**row)
        return Envelope[RemediationItemResponse](
            data=response,
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"remediation lookup failed: {exc}") from exc


@router.patch("/{remediation_id}", response_model=Envelope[RemediationItemResponse])
def remediations_update(
    run_id: str,
    remediation_id: str,
    request: RemediationUpdateRequest,
) -> Envelope[RemediationItemResponse]:
    try:
        updated = update_remediation(
            run_id=run_id,
            remediation_id=remediation_id,
            owner=request.owner,
            due_date=request.due_date,
            status=request.status,
            action_required=request.action_required,
            note=request.note,
            evidence_links=request.evidence_links,
        )
        response = RemediationItemResponse(**updated)
        return Envelope[RemediationItemResponse](
            data=response,
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"remediation update failed: {exc}") from exc
