from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.real_dataset_run_service import (
    fetch_all_allowed_real_sources,
    fetch_real_source_to_dataset,
)


class RealDatasetRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    dataset_id: str
    fetch_metadata: dict
    paths: dict
    deterministic_authoritative: bool


class RealDatasetRunBulkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success_count: int
    failure_count: int
    successes: list[dict]
    failures: list[dict]
    deterministic_authoritative: bool


router = APIRouter(prefix="/v1/real-dataset-runs", tags=["real-dataset-runs"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.post("/sources/{source_id}/fetch", response_model=Envelope[RealDatasetRunResponse])
def real_dataset_fetch_one(source_id: str) -> Envelope[RealDatasetRunResponse]:
    try:
        payload = fetch_real_source_to_dataset(source_id=source_id)
        return Envelope[RealDatasetRunResponse](
            data=RealDatasetRunResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"real dataset fetch failed: {exc}") from exc


@router.post("/fetch-all", response_model=Envelope[RealDatasetRunBulkResponse])
def real_dataset_fetch_all() -> Envelope[RealDatasetRunBulkResponse]:
    try:
        payload = fetch_all_allowed_real_sources()
        return Envelope[RealDatasetRunBulkResponse](
            data=RealDatasetRunBulkResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"bulk real dataset fetch failed: {exc}") from exc
