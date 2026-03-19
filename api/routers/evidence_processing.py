from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.evidence_processing_service import (
    EvidenceProcessingError,
    build_corpus_readiness,
    process_all_evidence_for_pack,
    process_evidence_item,
)


class EvidenceProcessingItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    filename: str
    title: str
    source_type: str
    detected_mime: str
    size_bytes: int
    sha256: str
    storage_path: str
    citation: str
    processing_status: str
    malware_scan_status: str
    ocr_status: str
    created_at: str
    updated_at: str | None = None
    extracted_text_path: str | None = None
    classification: dict | None = None
    classification_path: str | None = None
    key_facts: dict | None = None
    key_facts_path: str | None = None
    error_detail: str | None = None


class CorpusReadinessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: str
    item_count: int
    ready_count: int
    failed_count: int
    pending_count: int
    corpus_ready: bool
    statuses: dict[str, int]
    failures: list[dict]
    event: str | None = None


class BulkProcessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: str
    processed_count: int
    failure_count: int
    failures: list[dict]
    readiness: CorpusReadinessResponse


router = APIRouter(prefix="/v1/evidence-packs/{pack_id}/processing", tags=["evidence-processing"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.post("/items/{evidence_id}", response_model=Envelope[EvidenceProcessingItemResponse])
def processing_item(pack_id: str, evidence_id: str) -> Envelope[EvidenceProcessingItemResponse]:
    try:
        row = process_evidence_item(pack_id=pack_id, evidence_id=evidence_id)
        return Envelope[EvidenceProcessingItemResponse](
            data=EvidenceProcessingItemResponse(**row),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EvidenceProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"evidence processing failed: {exc}") from exc


@router.post("/run", response_model=Envelope[BulkProcessResponse])
def processing_run(pack_id: str) -> Envelope[BulkProcessResponse]:
    try:
        payload = process_all_evidence_for_pack(pack_id=pack_id)
        return Envelope[BulkProcessResponse](
            data=BulkProcessResponse(
                pack_id=payload["pack_id"],
                processed_count=payload["processed_count"],
                failure_count=payload["failure_count"],
                failures=payload["failures"],
                readiness=CorpusReadinessResponse(**payload["readiness"]),
            ),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EvidenceProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"bulk evidence processing failed: {exc}") from exc


@router.get("/readiness", response_model=Envelope[CorpusReadinessResponse])
def processing_readiness(pack_id: str) -> Envelope[CorpusReadinessResponse]:
    try:
        payload = build_corpus_readiness(pack_id=pack_id)
        return Envelope[CorpusReadinessResponse](
            data=CorpusReadinessResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EvidenceProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"readiness lookup failed: {exc}") from exc
