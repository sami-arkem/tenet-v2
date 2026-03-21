from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.dataset_ingestion_service import (
    get_dataset_ingestion_status,
    ingest_all_datasets,
    ingest_dataset,
    search_dataset_index,
)


class DatasetIngestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    title: str
    domain: str
    jurisdictions: list[str]
    countries: list[str]
    framework_ids: list[str]
    dataset_type: str
    license_type: str
    status: str
    loader_kind: str
    retrieval_ready: bool
    normalized_text_path: str
    chunks_path: str
    index_path: str
    chunk_count: int
    ingested_at: str


class DatasetBulkIngestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    processed_count: int
    failure_count: int
    processed: list[dict]
    failures: list[dict]


class DatasetSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    query: str
    result_count: int
    results: list[dict]


router = APIRouter(prefix="/v1/dataset-ingestion", tags=["dataset-ingestion"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.post("/datasets/{dataset_id}/ingest", response_model=Envelope[DatasetIngestionResponse])
def dataset_ingest(dataset_id: str) -> Envelope[DatasetIngestionResponse]:
    try:
        payload = ingest_dataset(dataset_id=dataset_id)
        return Envelope[DatasetIngestionResponse](
            data=DatasetIngestionResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"dataset ingestion failed: {exc}") from exc


@router.post("/ingest-all", response_model=Envelope[DatasetBulkIngestionResponse])
def dataset_ingest_all(only_active: bool = Query(default=True)) -> Envelope[DatasetBulkIngestionResponse]:
    try:
        payload = ingest_all_datasets(only_active=only_active)
        return Envelope[DatasetBulkIngestionResponse](
            data=DatasetBulkIngestionResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"bulk dataset ingestion failed: {exc}") from exc


@router.get("/datasets/{dataset_id}/status", response_model=Envelope[DatasetIngestionResponse])
def dataset_ingestion_status(dataset_id: str) -> Envelope[DatasetIngestionResponse]:
    try:
        payload = get_dataset_ingestion_status(dataset_id=dataset_id)
        return Envelope[DatasetIngestionResponse](
            data=DatasetIngestionResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"dataset ingestion status failed: {exc}") from exc


@router.get("/datasets/{dataset_id}/search", response_model=Envelope[DatasetSearchResponse])
def dataset_search(dataset_id: str, query: str, top_k: int = 8) -> Envelope[DatasetSearchResponse]:
    try:
        payload = search_dataset_index(dataset_id=dataset_id, query=query, top_k=top_k)
        return Envelope[DatasetSearchResponse](
            data=DatasetSearchResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"dataset search failed: {exc}") from exc
