from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.review_service import build_review_summary, submit_review_decision


class ReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewer: str
    decision: str
    rationale: str
    conditions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    note: str | None = None


class ReviewRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewed_at: str
    reviewer: str
    decision: str
    rationale: str
    conditions: list[str]
    evidence_refs: list[str]
    note: str | None = None


class ReviewSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: str
    baseline: dict[str, Any]
    export_package: dict[str, Any]
    latest_review: ReviewRecordResponse | None = None
    review_count: int
    approved: bool
    conditionally_approved: bool
    rejected: bool
    review_history: list[ReviewRecordResponse]
    created_at: str
    updated_at: str


router = APIRouter(prefix="/v1/audits/{run_id}/review", tags=["review"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.get("", response_model=Envelope[ReviewSummaryResponse])
def review_get(run_id: str) -> Envelope[ReviewSummaryResponse]:
    try:
        summary = build_review_summary(run_id)
        latest = summary["latest_review"]
        response = ReviewSummaryResponse(
            run_id=summary["run_id"],
            status=summary["status"],
            baseline=summary["baseline"],
            export_package=summary["export_package"],
            latest_review=ReviewRecordResponse(**latest) if isinstance(latest, dict) else None,
            review_count=summary["review_count"],
            approved=summary["approved"],
            conditionally_approved=summary["conditionally_approved"],
            rejected=summary["rejected"],
            review_history=[ReviewRecordResponse(**row) for row in summary["review_history"]],
            created_at=summary["created_at"],
            updated_at=summary["updated_at"],
        )
        return Envelope[ReviewSummaryResponse](
            data=response,
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"review lookup failed: {exc}") from exc


@router.post("", response_model=Envelope[ReviewSummaryResponse])
def review_submit(run_id: str, request: ReviewDecisionRequest) -> Envelope[ReviewSummaryResponse]:
    try:
        submit_review_decision(
            run_id=run_id,
            reviewer=request.reviewer,
            decision=request.decision,
            rationale=request.rationale,
            conditions=request.conditions,
            evidence_refs=request.evidence_refs,
            note=request.note,
        )
        summary = build_review_summary(run_id)
        latest = summary["latest_review"]
        response = ReviewSummaryResponse(
            run_id=summary["run_id"],
            status=summary["status"],
            baseline=summary["baseline"],
            export_package=summary["export_package"],
            latest_review=ReviewRecordResponse(**latest) if isinstance(latest, dict) else None,
            review_count=summary["review_count"],
            approved=summary["approved"],
            conditionally_approved=summary["conditionally_approved"],
            rejected=summary["rejected"],
            review_history=[ReviewRecordResponse(**row) for row in summary["review_history"]],
            created_at=summary["created_at"],
            updated_at=summary["updated_at"],
        )
        return Envelope[ReviewSummaryResponse](
            data=response,
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"review submit failed: {exc}") from exc
