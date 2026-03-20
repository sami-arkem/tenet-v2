"""
Auth middleware — Bible §4.3.
Validates JWT or API key, sets request.state.user/tenant.
"""
from __future__ import annotations

import hashlib
from typing import Any

from fastapi import Request
from jose import JWTError, jwt
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.db.connection import AsyncSessionLocal

# Routes that bypass authentication
PUBLIC_ROUTES: frozenset[str] = frozenset({
    "/v1/auth/login",
    "/v1/auth/signup",
    "/v1/auth/verify-email",
    "/v1/auth/forgot-password",
    "/v1/auth/reset-password",
    "/v1/jurisdiction-packs",  # List all packs
    "/health",
    "/metrics",
    "/docs",
    "/openapi.json",
})

# Paths that are public (reference data, not tenant-specific)
PUBLIC_PATH_PREFIXES: tuple[str, ...] = (
    "/v1/jurisdiction-packs/",  # Jurisdiction pack details and controls
)

_UNAUTHORIZED = JSONResponse(
    status_code=401,
    content={
        "data": None,
        "error": {"code": "UNAUTHORIZED", "message": "Authentication required"},
        "meta": {},
    },
)

_SUSPENDED = JSONResponse(
    status_code=403,
    content={
        "data": None,
        "error": {"code": "TENANT_SUSPENDED", "message": "Account suspended"},
        "meta": {},
    },
)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Any:
        # Check exact public routes first
        if request.url.path in PUBLIC_ROUTES:
            return await call_next(request)

        # Special handling for jurisdiction packs (all endpoints including list and details)
        if request.url.path.startswith("/v1/jurisdiction-packs"):
            return await call_next(request)

        # Check public path prefixes
        if any(request.url.path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")
        # Dev-mode shortcut: X-User-ID (frontend uses this for now)
        dev_user_id = request.headers.get("X-User-ID")

        if not auth_header and not api_key_header and not dev_user_id:
            return _UNAUTHORIZED

        try:
            async with AsyncSessionLocal() as db:
                if dev_user_id and settings.ENVIRONMENT in ("development", "test"):
                    user = await _load_user_by_id(db, dev_user_id)
                elif api_key_header:
                    user = await _authenticate_api_key(db, api_key_header)
                else:
                    token = _extract_bearer(auth_header or "")
                    if not token:
                        return _UNAUTHORIZED
                    user = await _authenticate_jwt(db, token)

            if not user:
                return _UNAUTHORIZED
            if not user.get("is_active"):
                return _SUSPENDED
            if user.get("tenant_suspended"):
                return _SUSPENDED

            request.state.user_id = str(user["id"])
            request.state.tenant_id = str(user["tenant_id"])
            request.state.user_role = user["role"]
            request.state.user = user

        except Exception as exc:
            return JSONResponse(
                status_code=401,
                content={
                    "data": None,
                    "error": {"code": "TOKEN_INVALID", "message": str(exc)},
                    "meta": {},
                },
            )

        return await call_next(request)


def _extract_bearer(auth_header: str) -> str | None:
    parts = auth_header.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


async def _load_user_by_id(db: Any, user_id: str) -> dict | None:
    result = await db.execute(
        text(
            """
            SELECT u.id, u.tenant_id, u.email, u.full_name, u.role, u.is_active,
                   t.is_suspended AS tenant_suspended
            FROM users u
            JOIN tenants t ON t.id = u.tenant_id
            WHERE u.id = :uid
            """
        ),
        {"uid": user_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def _authenticate_jwt(db: Any, token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub", "")
    except JWTError as exc:
        raise ValueError(str(exc)) from exc
    return await _load_user_by_id(db, user_id)


async def _authenticate_api_key(db: Any, raw_key: str) -> dict | None:
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    result = await db.execute(
        text(
            """
            SELECT u.id, u.tenant_id, u.email, u.role, u.is_active,
                   t.is_suspended AS tenant_suspended
            FROM api_keys k
            JOIN tenants t ON t.id = k.tenant_id
            -- api keys belong to tenant, not to a specific user — use tenant owner
            JOIN users u ON u.tenant_id = k.tenant_id AND u.role = 'owner'
            WHERE k.key_hash = :key_hash AND k.is_active = TRUE
              AND (k.expires_at IS NULL OR k.expires_at > NOW())
            LIMIT 1
            """
        ),
        {"key_hash": key_hash},
    )
    row = result.mappings().first()
    if row:
        # Update last_used_at
        await db.execute(
            text("UPDATE api_keys SET last_used_at = NOW() WHERE key_hash = :kh"),
            {"kh": key_hash},
        )
    return dict(row) if row else None
