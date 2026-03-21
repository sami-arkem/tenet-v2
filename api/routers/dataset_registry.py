from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.dataset_registry_service import (
    build_dataset_coverage_summary,
    filter_datasets,
    load_dataset_registry,
    seed_example_datasets,
)


class DatasetRegistryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: str
    count: int
    items: list[dict]
    errors: list[dict]


class DatasetCoverageSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deterministic_authoritative: bool
    registry_count: int
    retrieval_ready_count: int
    active_count: int
    coverage: dict
    validation: dict
    generated_at: str


class DatasetFilterResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int
    items: list[dict]


class DatasetSeedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    created: list[str]


router = APIRouter(prefix="/v1/dataset-registry", tags=["dataset-registry"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.get("", response_model=Envelope[DatasetRegistryResponse])
def dataset_registry_list() -> Envelope[DatasetRegistryResponse]:
    try:
        payload = load_dataset_registry()
        return Envelope[DatasetRegistryResponse](
            data=DatasetRegistryResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"dataset registry failed: {exc}") from exc


@router.get("/coverage", response_model=Envelope[DatasetCoverageSummaryResponse])
def dataset_registry_coverage() -> Envelope[DatasetCoverageSummaryResponse]:
    try:
        payload = build_dataset_coverage_summary()
        return Envelope[DatasetCoverageSummaryResponse](
            data=DatasetCoverageSummaryResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"dataset coverage failed: {exc}") from exc


@router.get("/filter", response_model=Envelope[DatasetFilterResponse])
def dataset_registry_filter(
    domain: str | None = Query(default=None),
    jurisdiction: str | None = Query(default=None),
    country: str | None = Query(default=None),
    framework_id: str | None = Query(default=None),
    dataset_type: str | None = Query(default=None),
    retrieval_ready_only: bool = Query(default=False),
) -> Envelope[DatasetFilterResponse]:
    try:
        payload = filter_datasets(
            domain=domain,
            jurisdiction=jurisdiction,
            country=country,
            framework_id=framework_id,
            dataset_type=dataset_type,
            retrieval_ready_only=retrieval_ready_only,
        )
        return Envelope[DatasetFilterResponse](
            data=DatasetFilterResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"dataset filter failed: {exc}") from exc


@router.post("/seed-examples", response_model=Envelope[DatasetSeedResponse])
def dataset_registry_seed_examples() -> Envelope[DatasetSeedResponse]:
    try:
        payload = seed_example_datasets()
        return Envelope[DatasetSeedResponse](
            data=DatasetSeedResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"dataset seed failed: {exc}") from exc
