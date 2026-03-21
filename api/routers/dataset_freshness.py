from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.dataset_freshness_service import (
    build_dataset_freshness_registry,
    build_refresh_plan,
    get_dataset_freshness_status,
)


class DatasetFreshnessRegistryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deterministic_authoritative: bool
    dataset_count: int
    fresh: int
    stale: int
    expired: int
    unknown: int
    refresh_due_count: int
    items: list[dict]
    generated_at: str


class DatasetFreshnessItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    title: str
    domain: str | None = None
    jurisdictions: list[str]
    countries: list[str]
    framework_ids: list[str]
    dataset_type: str | None = None
    license_type: str | None = None
    status: str
    update_cadence: str
    retrieval_ready: bool
    last_refresh_date: str | None = None
    age_days: int | None = None
    freshness_state: str
    next_refresh_date: str
    refresh_due: bool
    refresh_allowed: bool
    priority: str
    deterministic_authoritative: bool
    evaluated_at: str


class DatasetRefreshPlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deterministic_authoritative: bool
    candidate_count: int
    scheduled_count: int
    items: list[dict]
    generated_at: str


router = APIRouter(prefix="/v1/dataset-freshness", tags=["dataset-freshness"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.post("/rebuild", response_model=Envelope[DatasetFreshnessRegistryResponse])
def dataset_freshness_rebuild() -> Envelope[DatasetFreshnessRegistryResponse]:
    try:
        payload = build_dataset_freshness_registry()
        return Envelope[DatasetFreshnessRegistryResponse](
            data=DatasetFreshnessRegistryResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"dataset freshness rebuild failed: {exc}") from exc


@router.get("/datasets/{dataset_id}", response_model=Envelope[DatasetFreshnessItemResponse])
def dataset_freshness_item(dataset_id: str) -> Envelope[DatasetFreshnessItemResponse]:
    try:
        payload = get_dataset_freshness_status(dataset_id=dataset_id)
        return Envelope[DatasetFreshnessItemResponse](
            data=DatasetFreshnessItemResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"dataset freshness lookup failed: {exc}") from exc


@router.get("/refresh-plan", response_model=Envelope[DatasetRefreshPlanResponse])
def dataset_refresh_plan(limit: int = Query(default=50)) -> Envelope[DatasetRefreshPlanResponse]:
    try:
        payload = build_refresh_plan(limit=limit)
        return Envelope[DatasetRefreshPlanResponse](
            data=DatasetRefreshPlanResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"dataset refresh plan failed: {exc}") from exc
