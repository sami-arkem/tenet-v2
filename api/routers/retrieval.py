from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.retrieval_service import (
    build_audit_context_pack,
    build_pack_retrieval_index,
    load_pack_retrieval_index,
    search_pack_corpus,
)


class RetrievalBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_token_target: int = 180
    chunk_overlap: int = 40


class RetrievalIndexResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: str
    chunk_token_target: int
    chunk_overlap: int
    document_count: int
    chunk_count: int
    documents: list[dict]
    chunks: list[dict]
    document_frequency: dict


class RetrievalSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    top_k: int = 8


class RetrievalSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: str
    query: str
    result_count: int
    results: list[dict]


class AuditContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_questions: list[str] = Field(min_length=1)
    top_k_per_question: int = 5


class AuditContextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: str
    question_count: int
    selected_chunk_count: int
    questions: list[dict]


router = APIRouter(prefix="/v1/retrieval", tags=["retrieval"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.post("/evidence-packs/{pack_id}/build", response_model=Envelope[RetrievalIndexResponse])
def retrieval_build(pack_id: str, request: RetrievalBuildRequest) -> Envelope[RetrievalIndexResponse]:
    try:
        payload = build_pack_retrieval_index(
            pack_id=pack_id,
            chunk_token_target=request.chunk_token_target,
            chunk_overlap=request.chunk_overlap,
        )
        return Envelope[RetrievalIndexResponse](
            data=RetrievalIndexResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"retrieval build failed: {exc}") from exc


@router.get("/evidence-packs/{pack_id}/index", response_model=Envelope[RetrievalIndexResponse])
def retrieval_index(pack_id: str) -> Envelope[RetrievalIndexResponse]:
    try:
        payload = load_pack_retrieval_index(pack_id=pack_id)
        return Envelope[RetrievalIndexResponse](
            data=RetrievalIndexResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"retrieval index lookup failed: {exc}") from exc


@router.post("/evidence-packs/{pack_id}/search", response_model=Envelope[RetrievalSearchResponse])
def retrieval_search(pack_id: str, request: RetrievalSearchRequest) -> Envelope[RetrievalSearchResponse]:
    try:
        payload = search_pack_corpus(
            pack_id=pack_id,
            query=request.query,
            top_k=request.top_k,
        )
        return Envelope[RetrievalSearchResponse](
            data=RetrievalSearchResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"retrieval search failed: {exc}") from exc


@router.post("/evidence-packs/{pack_id}/audit-context", response_model=Envelope[AuditContextResponse])
def retrieval_audit_context(pack_id: str, request: AuditContextRequest) -> Envelope[AuditContextResponse]:
    try:
        payload = build_audit_context_pack(
            pack_id=pack_id,
            audit_questions=request.audit_questions,
            top_k_per_question=request.top_k_per_question,
        )
        return Envelope[AuditContextResponse](
            data=AuditContextResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"audit context build failed: {exc}") from exc
