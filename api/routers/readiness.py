from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.readiness_service import build_readiness_plan


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: str
    pack_name: str
    company_name: str | None = None
    audit_type: str | None = None
    domain: str | None = None
    jurisdictions: list[str]
    summary: dict[str, Any]
    controls: list[dict[str, Any]]
    requested_evidence_actions: list[dict[str, Any]]
    corpus_readiness: dict[str, Any]


router = APIRouter(prefix="/v1/evidence-packs", tags=["readiness"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.get("/{pack_id}/readiness", response_model=Envelope[ReadinessResponse])
def evidence_pack_readiness(pack_id: str) -> Envelope[ReadinessResponse]:
    try:
        row = build_readiness_plan(pack_id)
        return Envelope[ReadinessResponse](
            data=ReadinessResponse(**row),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"readiness build failed: {exc}") from exc
