from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.job_manager import get_job, list_jobs, submit_job


class JobSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_type: str
    payload: dict[str, Any]


class JobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    job_type: str
    queue_name: str
    status: str
    payload: dict[str, Any]
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    retry_count: int
    max_retries: int
    time_limit_seconds: int
    created_at: str
    updated_at: str
    started_at: str | None = None
    finished_at: str | None = None
    timeline: list[dict[str, Any]]


class JobListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[JobResponse]


router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.get("", response_model=Envelope[JobListResponse])
def jobs_list() -> Envelope[JobListResponse]:
    try:
        items = [JobResponse(**row) for row in list_jobs()]
        return Envelope[JobListResponse](
            data=JobListResponse(items=items),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"job list failed: {exc}") from exc


@router.post("", response_model=Envelope[JobResponse])
def jobs_submit(request: JobSubmitRequest) -> Envelope[JobResponse]:
    try:
        row = submit_job(
            job_type=request.job_type,
            payload=request.payload,
        )
        return Envelope[JobResponse](
            data=JobResponse(**row),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"job submit failed: {exc}") from exc


@router.get("/{job_id}", response_model=Envelope[JobResponse])
def jobs_get(job_id: str) -> Envelope[JobResponse]:
    try:
        row = get_job(job_id)
        return Envelope[JobResponse](
            data=JobResponse(**row),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"job lookup failed: {exc}") from exc
