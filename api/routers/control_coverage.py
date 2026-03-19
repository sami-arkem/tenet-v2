from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.control_coverage_service import (
    build_control_coverage_matrix,
    get_control_coverage_matrix,
)


class ControlCoverageSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    control_count: int
    supported_controls: int
    partial_controls: int
    blocked_controls: int


class ControlCoverageRowResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    control_id: str
    regime_id: str
    title: str
    coverage_status: str
    declared_control_present: bool
    declared_operating_effective: bool | None = None
    required_evidence_types: list[str]
    covered_evidence_types: list[str]
    missing_required_evidence_types: list[str]
    direct_evidence: list[dict]
    context_matches: list[dict]
    rationale: str
    deterministic_authoritative: bool


class ControlCoverageMatrixResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    generated_at: str | None = None
    deterministic_authoritative: bool
    company_name: str | None = None
    audit_type: str | None = None
    summary: ControlCoverageSummaryResponse
    controls: list[ControlCoverageRowResponse]


router = APIRouter(prefix="/v1/control-coverage", tags=["control-coverage"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.post("/audits/{run_id}/build", response_model=Envelope[ControlCoverageMatrixResponse])
def control_coverage_build(run_id: str) -> Envelope[ControlCoverageMatrixResponse]:
    try:
        payload = build_control_coverage_matrix(run_id=run_id)
        return Envelope[ControlCoverageMatrixResponse](
            data=ControlCoverageMatrixResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"control coverage build failed: {exc}") from exc


@router.get("/audits/{run_id}", response_model=Envelope[ControlCoverageMatrixResponse])
def control_coverage_get(run_id: str) -> Envelope[ControlCoverageMatrixResponse]:
    try:
        payload = get_control_coverage_matrix(run_id=run_id)
        return Envelope[ControlCoverageMatrixResponse](
            data=ControlCoverageMatrixResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"control coverage lookup failed: {exc}") from exc
