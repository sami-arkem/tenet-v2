from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.audit_context_service import (
    build_default_audit_questions,
    build_retrieval_grounded_context_pack,
    get_context_pack,
)


class AuditContextBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_questions: list[str] | None = None
    top_k_per_question: int = 5
    ensure_retrieval_index: bool = True


class AuditContextQuestionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: str
    questions: list[str]


class AuditContextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: str
    pack_name: str
    generated_at: str
    deterministic_authoritative: bool
    company_profile: dict
    scope: dict
    plan_summary: dict
    readiness_summary: dict
    corpus_readiness: dict
    retrieval_index_summary: dict
    questions: list[dict]
    selected_chunk_count: int
    question_count: int


router = APIRouter(prefix="/v1/audit-context", tags=["audit-context"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.get("/evidence-packs/{pack_id}/questions", response_model=Envelope[AuditContextQuestionsResponse])
def audit_context_questions(pack_id: str) -> Envelope[AuditContextQuestionsResponse]:
    try:
        questions = build_default_audit_questions(pack_id=pack_id)
        return Envelope[AuditContextQuestionsResponse](
            data=AuditContextQuestionsResponse(pack_id=pack_id, questions=questions),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"audit context questions failed: {exc}") from exc


@router.post("/evidence-packs/{pack_id}/build", response_model=Envelope[AuditContextResponse])
def audit_context_build(pack_id: str, request: AuditContextBuildRequest) -> Envelope[AuditContextResponse]:
    try:
        payload = build_retrieval_grounded_context_pack(
            pack_id=pack_id,
            audit_questions=request.audit_questions,
            top_k_per_question=request.top_k_per_question,
            ensure_retrieval_index=request.ensure_retrieval_index,
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


@router.get("/evidence-packs/{pack_id}", response_model=Envelope[AuditContextResponse])
def audit_context_get(pack_id: str) -> Envelope[AuditContextResponse]:
    try:
        payload = get_context_pack(pack_id=pack_id)
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
        raise HTTPException(status_code=500, detail=f"audit context lookup failed: {exc}") from exc
