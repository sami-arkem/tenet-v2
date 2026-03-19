from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from core.remediation_operator_service import load_actor_directory


PUBLIC_ROUTES = {
    "/health",
    "/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID") or os.urandom(8).hex()
        request.state.run_id = request.headers.get("X-Run-ID")
        request.state.timestamp = _now_iso()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        if request.state.run_id:
            response.headers["X-Run-ID"] = request.state.run_id
        return response


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_ROUTES:
            return await call_next(request)

        actor_dir_path = os.getenv("TENET_ACTOR_DIRECTORY_PATH")
        actor_directory: dict[str, dict[str, Any]] = {}
        if actor_dir_path:
            actor_directory = load_actor_directory(Path(actor_dir_path))

        request.app.state.actor_directory = actor_directory

        user_id = request.headers.get("X-User-ID")
        if not user_id:
            return JSONResponse(
                status_code=401,
                content={
                    "data": None,
                    "meta": {
                        "request_id": getattr(request.state, "request_id", "unknown"),
                        "timestamp": getattr(request.state, "timestamp", _now_iso()),
                        "version": "1.0",
                        "run_id": getattr(request.state, "run_id", None),
                    },
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Authentication required",
                        "details": None,
                    },
                },
            )

        actor = actor_directory.get(user_id)
        if actor is None:
            return JSONResponse(
                status_code=401,
                content={
                    "data": None,
                    "meta": {
                        "request_id": getattr(request.state, "request_id", "unknown"),
                        "timestamp": getattr(request.state, "timestamp", _now_iso()),
                        "version": "1.0",
                        "run_id": getattr(request.state, "run_id", None),
                    },
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Authentication required",
                        "details": {"user_id": user_id},
                    },
                },
            )

        request.state.user_id = user_id
        request.state.tenant_id = str(actor["tenant_id"])
        request.state.user_role = str(actor["role"]).upper()

        return await call_next(request)
