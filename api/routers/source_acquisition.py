from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.source_acquisition_service import (
    build_source_registry_summary,
    evaluate_source_for_ingestion,
    evaluate_source_for_ingestion_enhanced,
    load_source_registry,
    rebuild_source_index,
    seed_example_sources,
)


class SourceRegistryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: str
    count: int
    items: list[dict]
    errors: list[dict]


class SourceSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deterministic_authoritative: bool
    registry_count: int
    approved_count: int
    retrieval_allowed_count: int
    coverage: dict
    validation: dict


class SourceEvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    decision: str
    reasons: list[str]
    source: dict
    provenance_checks: dict | None = None


class SourceSeedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    created: list[str]


class SourceIndexResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indexed: int
    status: str


router = APIRouter(prefix="/v1/source-acquisition", tags=["source-acquisition"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.get("", response_model=Envelope[SourceRegistryResponse])
def source_registry_list() -> Envelope[SourceRegistryResponse]:
    try:
        payload = load_source_registry()
        return Envelope[SourceRegistryResponse](
            data=SourceRegistryResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"source registry failed: {exc}") from exc


@router.get("/summary", response_model=Envelope[SourceSummaryResponse])
def source_registry_summary() -> Envelope[SourceSummaryResponse]:
    try:
        payload = build_source_registry_summary()
        return Envelope[SourceSummaryResponse](
            data=SourceSummaryResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"source summary failed: {exc}") from exc


@router.post("/seed-examples", response_model=Envelope[SourceSeedResponse])
def source_seed_examples() -> Envelope[SourceSeedResponse]:
    try:
        payload = seed_example_sources()
        return Envelope[SourceSeedResponse](
            data=SourceSeedResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"source seed failed: {exc}") from exc


@router.post("/rebuild-index", response_model=Envelope[SourceIndexResponse])
def source_rebuild_index() -> Envelope[SourceIndexResponse]:
    try:
        idx = rebuild_source_index()
        return Envelope[SourceIndexResponse](
            data=SourceIndexResponse(indexed=len(idx), status="compiled"),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"source index rebuild failed: {exc}") from exc


@router.get("/sources/{source_id}/evaluate", response_model=Envelope[SourceEvaluationResponse])
def source_evaluate(source_id: str) -> Envelope[SourceEvaluationResponse]:
    try:
        payload = evaluate_source_for_ingestion(source_id=source_id)
        return Envelope[SourceEvaluationResponse](
            data=SourceEvaluationResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"source evaluation failed: {exc}") from exc


@router.get("/sources/{source_id}/evaluate-enhanced", response_model=Envelope[SourceEvaluationResponse])
def source_evaluate_enhanced(source_id: str) -> Envelope[SourceEvaluationResponse]:
    try:
        payload = evaluate_source_for_ingestion_enhanced(source_id=source_id)
        return Envelope[SourceEvaluationResponse](
            data=SourceEvaluationResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"enhanced source evaluation failed: {exc}") from exc
