from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.model_augmentation_service import (
    augment_audit_report_with_models,
    augment_evidence_item_with_models,
    augment_pack_evidence_with_models,
    get_audit_report_augmentation,
)


class EvidenceAugmentationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    filename: str | None = None
    title: str | None = None
    non_authoritative: bool
    classification: dict
    key_facts: dict


class PackEvidenceAugmentationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: str
    augmented_count: int
    failure_count: int
    failures: list[dict]
    items: list[EvidenceAugmentationResponse]


class AuditReportAugmentationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    non_authoritative: bool
    executive_narrative: dict
    gap_narratives: list[dict]


router = APIRouter(prefix="/v1/model-augmentation", tags=["model-augmentation"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.post("/evidence-packs/{pack_id}/items/{evidence_id}", response_model=Envelope[EvidenceAugmentationResponse])
def augment_single_evidence(pack_id: str, evidence_id: str) -> Envelope[EvidenceAugmentationResponse]:
    try:
        row = augment_evidence_item_with_models(
            pack_id=pack_id,
            evidence_id=evidence_id,
        )
        return Envelope[EvidenceAugmentationResponse](
            data=EvidenceAugmentationResponse(**row),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"evidence augmentation failed: {exc}") from exc


@router.post("/evidence-packs/{pack_id}/run", response_model=Envelope[PackEvidenceAugmentationResponse])
def augment_pack_evidence(pack_id: str) -> Envelope[PackEvidenceAugmentationResponse]:
    try:
        payload = augment_pack_evidence_with_models(pack_id=pack_id)
        return Envelope[PackEvidenceAugmentationResponse](
            data=PackEvidenceAugmentationResponse(
                pack_id=payload["pack_id"],
                augmented_count=payload["augmented_count"],
                failure_count=payload["failure_count"],
                failures=payload["failures"],
                items=[EvidenceAugmentationResponse(**row) for row in payload["items"]],
            ),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"pack augmentation failed: {exc}") from exc


@router.post("/audits/{run_id}/report", response_model=Envelope[AuditReportAugmentationResponse])
def augment_audit_report(run_id: str) -> Envelope[AuditReportAugmentationResponse]:
    try:
        payload = augment_audit_report_with_models(run_id=run_id)
        return Envelope[AuditReportAugmentationResponse](
            data=AuditReportAugmentationResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"audit report augmentation failed: {exc}") from exc


@router.get("/audits/{run_id}/report", response_model=Envelope[AuditReportAugmentationResponse])
def get_augmented_audit_report(run_id: str) -> Envelope[AuditReportAugmentationResponse]:
    try:
        payload = get_audit_report_augmentation(run_id=run_id)
        return Envelope[AuditReportAugmentationResponse](
            data=AuditReportAugmentationResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"audit report augmentation lookup failed: {exc}") from exc
