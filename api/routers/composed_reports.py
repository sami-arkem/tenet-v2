from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.report_composer import build_composed_report_bundle, build_composed_report_payload


class ComposedReportPayloadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    deterministic_authoritative: bool
    summary: dict
    company_profile: dict
    scope: dict
    findings: list[dict]
    remediation_items: list[dict]
    report_bundle: dict
    report_pack: dict
    model_augmentation: dict


class ComposedReportBundleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    markdown: str
    deterministic_authoritative: bool
    model_augmentation_present: bool
    overall_posture: str | None = None
    deployment_decision: str | None = None
    finding_count: int
    remediation_count: int


router = APIRouter(prefix="/v1/composed-reports", tags=["composed-reports"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.get("/{run_id}/payload", response_model=Envelope[ComposedReportPayloadResponse])
def composed_report_payload(run_id: str) -> Envelope[ComposedReportPayloadResponse]:
    try:
        payload = build_composed_report_payload(run_id=run_id)
        return Envelope[ComposedReportPayloadResponse](
            data=ComposedReportPayloadResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"composed report payload failed: {exc}") from exc


@router.get("/{run_id}/markdown", response_model=Envelope[ComposedReportBundleResponse])
def composed_report_markdown(run_id: str) -> Envelope[ComposedReportBundleResponse]:
    try:
        payload = build_composed_report_bundle(run_id=run_id)
        return Envelope[ComposedReportBundleResponse](
            data=ComposedReportBundleResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"composed report markdown failed: {exc}") from exc
