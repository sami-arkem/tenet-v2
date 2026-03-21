from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from apps.api.middleware.auth import AuthMiddleware, RequestContextMiddleware
from apps.api.routers import remediation, audits, findings, reports, evidence, evidence_jobs, upload_sessions, audit_preparation, ocr_submission


def _allowed_origins() -> list[str]:
    raw = os.getenv("TENET_ALLOWED_ORIGINS", "")
    if raw.strip():
        return [o.strip() for o in raw.split(",") if o.strip()]
    return ["http://localhost:3000", "http://localhost:5173"]


def _allowed_hosts() -> list[str] | None:
    raw = os.getenv("TENET_ALLOWED_HOSTS", "")
    if raw.strip():
        return [h.strip() for h in raw.split(",") if h.strip()]
    return None  # not configured — skip TrustedHostMiddleware


def create_app() -> FastAPI:
    app = FastAPI(
        title="Tenet API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    allowed_hosts = _allowed_hosts()
    if allowed_hosts is not None:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    origins = _allowed_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        # allow_credentials requires an explicit origin list, not a wildcard
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Run-ID"],
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(AuthMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/ready")
    async def ready():
        return {"status": "ready"}

    app.include_router(remediation.router, prefix="/v1/remediation", tags=["remediation"])
    app.include_router(audits.router, prefix="/v1/audits", tags=["audits"])
    app.include_router(findings.router, prefix="/v1/findings", tags=["findings"])
    app.include_router(reports.router, prefix="/v1/reports", tags=["reports"])
    app.include_router(evidence.router, prefix="/v1/evidence", tags=["evidence"])
    app.include_router(evidence_jobs.router, prefix="/v1/evidence-jobs", tags=["evidence-jobs"])
    app.include_router(upload_sessions.router, prefix="/v1/upload-sessions", tags=["upload-sessions"])
    app.include_router(audit_preparation.router, prefix="/v1/audit-preparation", tags=["audit-preparation"])
    app.include_router(ocr_submission.router, prefix="/v1/ocr-submissions", tags=["ocr-submissions"])

    return app


app = create_app()
