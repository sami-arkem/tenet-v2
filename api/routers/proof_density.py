from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.proof_density_service import (
    build_proof_density_summary,
    load_customer_pack_registry,
    load_gold_case_registry,
    seed_example_customer_pack,
    seed_example_gold_case,
)


class ProofDensitySummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deterministic_authoritative: bool
    targets: dict
    current: dict
    remaining: dict
    progress_percent: dict
    coverage: dict
    validation: dict


class RegistryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: str
    count: int
    items: list[dict]
    errors: list[dict]


class SeedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    created: dict


router = APIRouter(prefix="/v1/proof-density", tags=["proof-density"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.get("/summary", response_model=Envelope[ProofDensitySummaryResponse])
def proof_density_summary() -> Envelope[ProofDensitySummaryResponse]:
    try:
        payload = build_proof_density_summary()
        return Envelope[ProofDensitySummaryResponse](
            data=ProofDensitySummaryResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"proof density summary failed: {exc}") from exc


@router.get("/gold-cases", response_model=Envelope[RegistryResponse])
def proof_density_gold_cases() -> Envelope[RegistryResponse]:
    try:
        payload = load_gold_case_registry()
        return Envelope[RegistryResponse](
            data=RegistryResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"gold case registry failed: {exc}") from exc


@router.get("/customer-packs", response_model=Envelope[RegistryResponse])
def proof_density_customer_packs() -> Envelope[RegistryResponse]:
    try:
        payload = load_customer_pack_registry()
        return Envelope[RegistryResponse](
            data=RegistryResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"customer pack registry failed: {exc}") from exc


@router.post("/seed-examples", response_model=Envelope[SeedResponse])
def proof_density_seed_examples() -> Envelope[SeedResponse]:
    try:
        payload = {
            **seed_example_gold_case(),
            **seed_example_customer_pack(),
        }
        return Envelope[SeedResponse](
            data=SeedResponse(created=payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"proof density seed failed: {exc}") from exc
