"""
Tenet API — Bible §4.1 FastAPI application.
PostgreSQL-backed, JWT auth, full tenant isolation.
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.middleware.auth import AuthMiddleware
from app.middleware.tenant import TenantMiddleware
from app.routers import audits, auth, calendar, dashboard, entities, evidence, findings, jurisdiction_packs, monitoring, remediation, reports
from app.schemas.response import ApiResponse


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    # Startup — verify DB reachability
    from app.db.connection import engine
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        import logging
        logging.getLogger("tenet").error("Database not reachable: %s", exc)
    yield
    # Shutdown — dispose connection pool
    await engine.dispose()


app = FastAPI(
    title="Tenet API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT == "development" else None,
)

# ─── Security middleware ──────────────────────────────────────────────────────

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)
app.add_middleware(TenantMiddleware)


# ─── Request ID + timing ──────────────────────────────────────────────────────

@app.middleware("http")
async def add_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.middleware("http")
async def add_response_time(request: Request, call_next):  # type: ignore[no-untyped-def]
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time"] = f"{ms:.2f}ms"
    return response


# ─── Error handlers ───────────────────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", f"HTTP_{exc.status_code}")
        message = detail.get("message", str(exc.detail))
    else:
        code = f"HTTP_{exc.status_code}"
        message = str(detail)

    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.failure(
            code=code,
            message=message,
            request_id=getattr(request.state, "request_id", None),
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    import logging
    logging.getLogger("tenet").exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ApiResponse.failure(
            code="INTERNAL_ERROR",
            message="An internal error occurred",
            request_id=getattr(request.state, "request_id", None),
        ).model_dump(mode="json"),
    )


# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth.router,               prefix="/v1/auth",                tags=["auth"])
app.include_router(audits.router,             prefix="/v1/audits",              tags=["audits"])
app.include_router(findings.router,           prefix="/v1/findings",            tags=["findings"])
app.include_router(remediation.router,        prefix="/v1/remediation",         tags=["remediation"])
app.include_router(dashboard.router,          prefix="/v1/dashboard",           tags=["dashboard"])
app.include_router(evidence.router,           prefix="/v1/evidence",            tags=["evidence"])
app.include_router(reports.router,            prefix="/v1/reports",             tags=["reports"])
app.include_router(monitoring.router,         prefix="/v1/monitoring",          tags=["monitoring"])
app.include_router(calendar.router,           prefix="/v1/calendar",            tags=["calendar"])
app.include_router(entities.router,           prefix="/v1/entities",            tags=["entities"])
app.include_router(jurisdiction_packs.router, prefix="/v1/jurisdiction-packs",  tags=["jurisdiction-packs"])

# Audit preparation — mounted at /v1/audit-preparation for legacy frontend compat
from app.db import get_db  # noqa: E402
from fastapi import APIRouter as _PrepRouter
_prep = _PrepRouter()

@_prep.get("/{audit_id}")
async def _prep_fwd(audit_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    from app.routers.audits import get_audit_preparation
    return await get_audit_preparation(audit_id, request, db)

app.include_router(_prep, prefix="/v1/audit-preparation", tags=["audit-preparation"])


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"ok": True, "service": "tenet-api", "environment": settings.ENVIRONMENT}
