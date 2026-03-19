from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.finalize_release_service import (
    finalize_released_audit,
    get_release_finalization,
    render_release_finalization_markdown,
)


class ReleaseFinalizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_name: str | None = None
    package_version: str = "v1"
    include_model_augmentation: bool = True


class ReleaseFinalizationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    release_ready: bool
    release_status: str
    package_version: str
    released_package: dict
    release_gate: dict
    control_summary: dict
    dossier_summary: dict
    composed_report_summary: dict


class ReleaseFinalizationMarkdownResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    markdown: str
    deterministic_authoritative: bool


router = APIRouter(prefix="/v1/release-finalization", tags=["release-finalization"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.post("/audits/{run_id}/finalize", response_model=Envelope[ReleaseFinalizationResponse])
def release_finalize(run_id: str, request: ReleaseFinalizationRequest) -> Envelope[ReleaseFinalizationResponse]:
    try:
        payload = finalize_released_audit(
            run_id=run_id,
            package_name=request.package_name,
            package_version=request.package_version,
            include_model_augmentation=request.include_model_augmentation,
        )
        return Envelope[ReleaseFinalizationResponse](
            data=ReleaseFinalizationResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"release finalization failed: {exc}") from exc


@router.get("/audits/{run_id}", response_model=Envelope[ReleaseFinalizationResponse])
def release_finalization_get(run_id: str) -> Envelope[ReleaseFinalizationResponse]:
    try:
        payload = get_release_finalization(run_id=run_id)
        return Envelope[ReleaseFinalizationResponse](
            data=ReleaseFinalizationResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"release finalization lookup failed: {exc}") from exc


@router.get("/audits/{run_id}/markdown", response_model=Envelope[ReleaseFinalizationMarkdownResponse])
def release_finalization_markdown(run_id: str) -> Envelope[ReleaseFinalizationMarkdownResponse]:
    try:
        markdown = render_release_finalization_markdown(run_id=run_id)
        return Envelope[ReleaseFinalizationMarkdownResponse](
            data=ReleaseFinalizationMarkdownResponse(
                run_id=run_id,
                markdown=markdown,
                deterministic_authoritative=True,
            ),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"release finalization markdown failed: {exc}") from exc
