from __future__ import annotations

import base64

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.evidence_ingestion_service import EvidenceIngestionError, ingest_evidence_file, list_evidence_items


class EvidenceItemResponse(BaseModel):
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
    updated_at: str


class EvidenceListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[EvidenceItemResponse]


class EvidenceUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    title: str
    source_type: str
    citation: str
    content_base64: str


router = APIRouter(prefix="/v1/evidence-packs/{pack_id}/evidence", tags=["evidence"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.get("", response_model=Envelope[EvidenceListResponse])
def evidence_list(pack_id: str) -> Envelope[EvidenceListResponse]:
    try:
        rows = [EvidenceItemResponse(**row) for row in list_evidence_items(pack_id)]
        return Envelope[EvidenceListResponse](
            data=EvidenceListResponse(items=rows),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EvidenceIngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"evidence list failed: {exc}") from exc


@router.post("/upload", response_model=Envelope[EvidenceItemResponse])
def evidence_upload(
    pack_id: str,
    request: EvidenceUploadRequest,
) -> Envelope[EvidenceItemResponse]:
    try:
        try:
            data = base64.b64decode(request.content_base64, validate=True)
        except Exception as exc:
            raise EvidenceIngestionError("content_base64 must be valid base64") from exc
        row = ingest_evidence_file(
            pack_id=pack_id,
            filename=request.filename,
            data=data,
            title=request.title,
            source_type=request.source_type,
            citation=request.citation,
        )
        return Envelope[EvidenceItemResponse](
            data=EvidenceItemResponse(**row),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EvidenceIngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"evidence upload failed: {exc}") from exc
