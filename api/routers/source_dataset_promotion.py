from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.source_dataset_promotion_service import (
    promote_all_allowed_sources,
    promote_source_to_dataset_manifest,
)


class SourcePromotionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    override_domain: str | None = None
    override_framework_ids: list[str] = Field(default_factory=list)


class SourcePromotionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    decision: str
    dataset_manifest_path: str
    dataset_manifest: dict
    deterministic_authoritative: bool


class BulkSourcePromotionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    promoted_count: int
    skipped_count: int
    failure_count: int
    promoted: list[dict]
    skipped: list[dict]
    failures: list[dict]
    deterministic_authoritative: bool


router = APIRouter(prefix="/v1/source-dataset-promotion", tags=["source-dataset-promotion"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.post("/sources/{source_id}/promote", response_model=Envelope[SourcePromotionResponse])
def source_dataset_promote(source_id: str, request: SourcePromotionRequest) -> Envelope[SourcePromotionResponse]:
    try:
        payload = promote_source_to_dataset_manifest(
            source_id=source_id,
            override_domain=request.override_domain,
            override_framework_ids=request.override_framework_ids,
        )
        return Envelope[SourcePromotionResponse](
            data=SourcePromotionResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"source promotion failed: {exc}") from exc


@router.post("/promote-all", response_model=Envelope[BulkSourcePromotionResponse])
def source_dataset_promote_all() -> Envelope[BulkSourcePromotionResponse]:
    try:
        payload = promote_all_allowed_sources()
        return Envelope[BulkSourcePromotionResponse](
            data=BulkSourcePromotionResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"bulk source promotion failed: {exc}") from exc
