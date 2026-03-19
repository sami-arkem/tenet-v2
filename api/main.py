from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from api.routers.audits import router as audits_router
from api.routers.audit_context import router as audit_context_router
from api.routers.audit_dossier import router as audit_dossier_router
from api.routers.control_coverage import router as control_coverage_router
from api.routers.dataset_freshness import router as dataset_freshness_router
from api.routers.dataset_ingestion import router as dataset_ingestion_router
from api.routers.dataset_refresh_executor import router as dataset_refresh_executor_router
from api.routers.dataset_registry import router as dataset_registry_router
from api.routers.evidence import router as evidence_router
from api.routers.evidence_processing import router as evidence_processing_router
from api.routers.evidence_packs import router as evidence_packs_router
from api.routers.official_corpus import router as official_corpus_router
from api.routers.composed_reports import router as composed_reports_router
from api.routers.planning import router as planning_router
from api.routers.real_dataset_runs import router as real_dataset_runs_router
from api.routers.regulatory_monitor import router as regulatory_monitor_router
from api.routers.retrieval import router as retrieval_router
from api.routers.schedule_policy import router as schedule_policy_router
from api.routers.schedules import router as schedules_router
from api.routers.source_acquisition import router as source_acquisition_router
from api.routers.source_dataset_promotion import router as source_dataset_promotion_router
from api.routers.release_gate import router as release_gate_router
from api.routers.release_finalization import router as release_finalization_router
from api.routers.proof_density import router as proof_density_router
from api.routers.readiness import router as readiness_router
from api.routers.reviews import router as reviews_router
from api.routers.jobs import router as jobs_router
from api.routers.model_augmentation import router as model_augmentation_router
from api.routers.notifications import router as notifications_router
from api.routers.remediations import router as remediations_router
from api.routers.workflows import router as workflows_router
from api.routers.webhooks import router as webhooks_router
from api.schemas import Envelope, ErrorBody, HealthResponse, MetaBody
from api.store import new_request_id, utc_now_iso


app = FastAPI(
    title="Tenet API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        service="tenet-api",
        mode="deterministic",
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    envelope = Envelope[dict](
        data=None,
        meta=build_meta(),
        error=ErrorBody(
            code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            details=None,
        ),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope.model_dump(),
    )


app.include_router(audits_router)
app.include_router(audit_context_router)
app.include_router(audit_dossier_router)
app.include_router(control_coverage_router)
app.include_router(dataset_freshness_router)
app.include_router(dataset_ingestion_router)
app.include_router(dataset_refresh_executor_router)
app.include_router(dataset_registry_router)
app.include_router(regulatory_monitor_router)
app.include_router(release_gate_router)
app.include_router(remediations_router)
app.include_router(evidence_packs_router)
app.include_router(evidence_router)
app.include_router(evidence_processing_router)
app.include_router(official_corpus_router)
app.include_router(real_dataset_runs_router)
app.include_router(composed_reports_router)
app.include_router(retrieval_router)
app.include_router(schedule_policy_router)
app.include_router(schedules_router)
app.include_router(source_acquisition_router)
app.include_router(source_dataset_promotion_router)
app.include_router(release_finalization_router)
app.include_router(proof_density_router)
app.include_router(planning_router)
app.include_router(readiness_router)
app.include_router(reviews_router)
app.include_router(jobs_router)
app.include_router(model_augmentation_router)
app.include_router(notifications_router)
app.include_router(webhooks_router)
app.include_router(workflows_router)
