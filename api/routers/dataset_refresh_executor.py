from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.dataset_refresh_executor_service import (
    execute_dataset_refresh_run,
    get_dataset_refresh_run,
    list_dataset_refresh_runs,
)


class DatasetRefreshRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: str
    success_count: int
    failure_count: int
    items: list[dict]
    failures: list[dict]
    deterministic_authoritative: bool


class DatasetRefreshRunDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    requested_limit: int | None = None
    candidate_count: int | None = None
    scheduled_count: int | None = None
    success_count: int
    failure_count: int
    items: list[dict]
    failures: list[dict]
    deterministic_authoritative: bool


class DatasetRefreshRunListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int
    items: list[dict]
    deterministic_authoritative: bool


router = APIRouter(prefix="/v1/dataset-refresh-executor", tags=["dataset-refresh-executor"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.post("/run", response_model=Envelope[DatasetRefreshRunResponse])
def dataset_refresh_run(limit: int = Query(default=25)) -> Envelope[DatasetRefreshRunResponse]:
    try:
        payload = execute_dataset_refresh_run(limit=limit)
        return Envelope[DatasetRefreshRunResponse](
            data=DatasetRefreshRunResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"dataset refresh execution failed: {exc}") from exc


@router.get("/runs/{run_id}", response_model=Envelope[DatasetRefreshRunDetailResponse])
def dataset_refresh_get(run_id: str) -> Envelope[DatasetRefreshRunDetailResponse]:
    try:
        payload = get_dataset_refresh_run(run_id=run_id)
        return Envelope[DatasetRefreshRunDetailResponse](
            data=DatasetRefreshRunDetailResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"dataset refresh lookup failed: {exc}") from exc


@router.get("/runs", response_model=Envelope[DatasetRefreshRunListResponse])
def dataset_refresh_list() -> Envelope[DatasetRefreshRunListResponse]:
    try:
        payload = list_dataset_refresh_runs()
        return Envelope[DatasetRefreshRunListResponse](
            data=DatasetRefreshRunListResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"dataset refresh list failed: {exc}") from exc
