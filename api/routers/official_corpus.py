from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.official_corpus_bootstrap_service import (
    bootstrap_official_corpus,
    seed_official_sources,
)


class OfficialSeedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    created_count: int
    created: list[str]
    deterministic_authoritative: bool


class OfficialBootstrapResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deterministic_authoritative: bool
    seed: dict
    official_source_count: int
    promotion: dict
    ingestion: dict


router = APIRouter(prefix="/v1/official-corpus", tags=["official-corpus"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.post("/seed", response_model=Envelope[OfficialSeedResponse])
def official_corpus_seed() -> Envelope[OfficialSeedResponse]:
    try:
        payload = seed_official_sources()
        return Envelope[OfficialSeedResponse](
            data=OfficialSeedResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"official corpus seed failed: {exc}") from exc


@router.post("/bootstrap", response_model=Envelope[OfficialBootstrapResponse])
def official_corpus_bootstrap() -> Envelope[OfficialBootstrapResponse]:
    try:
        payload = bootstrap_official_corpus()
        return Envelope[OfficialBootstrapResponse](
            data=OfficialBootstrapResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"official corpus bootstrap failed: {exc}") from exc
