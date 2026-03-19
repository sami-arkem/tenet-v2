from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.release_gate_service import (
    build_release_gate,
    get_release_gate,
    render_release_gate_markdown,
)


class ReleaseGateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    deterministic_authoritative: bool
    release_status: str
    release_ready: bool
    company_name: str | None = None
    audit_type: str | None = None
    overall_posture: str | None = None
    deployment_decision: str | None = None
    control_summary: dict
    review_summary: dict
    export_summary: dict
    reasons_blocking_release: list[str]


class ReleaseGateMarkdownResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    deterministic_authoritative: bool
    markdown: str


router = APIRouter(prefix="/v1/release-gate", tags=["release-gate"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.post("/audits/{run_id}/build", response_model=Envelope[ReleaseGateResponse])
def release_gate_build(run_id: str) -> Envelope[ReleaseGateResponse]:
    try:
        payload = build_release_gate(run_id=run_id)
        return Envelope[ReleaseGateResponse](
            data=ReleaseGateResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"release gate build failed: {exc}") from exc


@router.get("/audits/{run_id}", response_model=Envelope[ReleaseGateResponse])
def release_gate_get(run_id: str) -> Envelope[ReleaseGateResponse]:
    try:
        payload = get_release_gate(run_id=run_id)
        return Envelope[ReleaseGateResponse](
            data=ReleaseGateResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"release gate lookup failed: {exc}") from exc


@router.get("/audits/{run_id}/markdown", response_model=Envelope[ReleaseGateMarkdownResponse])
def release_gate_markdown(run_id: str) -> Envelope[ReleaseGateMarkdownResponse]:
    try:
        markdown = render_release_gate_markdown(run_id=run_id)
        return Envelope[ReleaseGateMarkdownResponse](
            data=ReleaseGateMarkdownResponse(
                run_id=run_id,
                deterministic_authoritative=True,
                markdown=markdown,
            ),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"release gate markdown failed: {exc}") from exc
