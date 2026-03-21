from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.audit_dossier_service import (
    build_audit_dossier,
    get_audit_dossier,
    render_audit_dossier_markdown,
)


class AuditDossierResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    deterministic_authoritative: bool
    company_name: str | None = None
    audit_type: str | None = None
    overall_posture: str | None = None
    deployment_decision: str | None = None
    summary_text: str | None = None
    control_count: int | None = None
    supported_controls: int | None = None
    partial_controls: int | None = None
    blocked_controls: int | None = None
    controls: list[dict]


class AuditDossierMarkdownResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    markdown: str
    deterministic_authoritative: bool


router = APIRouter(prefix="/v1/audit-dossier", tags=["audit-dossier"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.post("/audits/{run_id}/build", response_model=Envelope[AuditDossierResponse])
def audit_dossier_build(run_id: str) -> Envelope[AuditDossierResponse]:
    try:
        payload = build_audit_dossier(run_id=run_id)
        return Envelope[AuditDossierResponse](
            data=AuditDossierResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"audit dossier build failed: {exc}") from exc


@router.get("/audits/{run_id}", response_model=Envelope[AuditDossierResponse])
def audit_dossier_get(run_id: str) -> Envelope[AuditDossierResponse]:
    try:
        payload = get_audit_dossier(run_id=run_id)
        return Envelope[AuditDossierResponse](
            data=AuditDossierResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"audit dossier lookup failed: {exc}") from exc


@router.get("/audits/{run_id}/markdown", response_model=Envelope[AuditDossierMarkdownResponse])
def audit_dossier_markdown(run_id: str) -> Envelope[AuditDossierMarkdownResponse]:
    try:
        markdown = render_audit_dossier_markdown(run_id=run_id)
        return Envelope[AuditDossierMarkdownResponse](
            data=AuditDossierMarkdownResponse(
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
        raise HTTPException(status_code=500, detail=f"audit dossier markdown failed: {exc}") from exc
