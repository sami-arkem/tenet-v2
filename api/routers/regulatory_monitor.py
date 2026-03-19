from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.regulatory_monitor_service import (
    get_monitor_run,
    get_regulatory_alert,
    list_monitor_runs,
    list_regulatory_alerts,
    run_regulatory_monitor,
)


class RegulatoryMonitorRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    deterministic_authoritative: bool
    started_at: str
    dataset_count: int
    created_alert_count: int
    unchanged_count: int
    alerts: list[dict]


class RegulatoryAlertListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int
    items: list[dict]
    deterministic_authoritative: bool


class RegulatoryMonitorRunListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int
    items: list[dict]
    deterministic_authoritative: bool


router = APIRouter(prefix="/v1/regulatory-monitor", tags=["regulatory-monitor"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.post("/run", response_model=Envelope[RegulatoryMonitorRunResponse])
def regulatory_monitor_run() -> Envelope[RegulatoryMonitorRunResponse]:
    try:
        payload = run_regulatory_monitor()
        return Envelope[RegulatoryMonitorRunResponse](
            data=RegulatoryMonitorRunResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"regulatory monitor run failed: {exc}") from exc


@router.get("/alerts", response_model=Envelope[RegulatoryAlertListResponse])
def regulatory_alerts() -> Envelope[RegulatoryAlertListResponse]:
    try:
        payload = list_regulatory_alerts()
        return Envelope[RegulatoryAlertListResponse](
            data=RegulatoryAlertListResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"regulatory alerts failed: {exc}") from exc


@router.get("/alerts/{alert_id}", response_model=Envelope[dict])
def regulatory_alert_get(alert_id: str) -> Envelope[dict]:
    try:
        payload = get_regulatory_alert(alert_id)
        return Envelope[dict](
            data=payload,
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"regulatory alert lookup failed: {exc}") from exc


@router.get("/runs", response_model=Envelope[RegulatoryMonitorRunListResponse])
def regulatory_monitor_runs() -> Envelope[RegulatoryMonitorRunListResponse]:
    try:
        payload = list_monitor_runs()
        return Envelope[RegulatoryMonitorRunListResponse](
            data=RegulatoryMonitorRunListResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"regulatory monitor run list failed: {exc}") from exc


@router.get("/runs/{run_id}", response_model=Envelope[dict])
def regulatory_monitor_run_get(run_id: str) -> Envelope[dict]:
    try:
        payload = get_monitor_run(run_id)
        return Envelope[dict](
            data=payload,
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"regulatory monitor run lookup failed: {exc}") from exc
