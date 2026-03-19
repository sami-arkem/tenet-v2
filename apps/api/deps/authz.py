from __future__ import annotations

from typing import Iterable

from fastapi import HTTPException, Request


def require_authenticated_user(request: Request) -> None:
    if not getattr(request.state, "user_id", None):
        raise HTTPException(
            status_code=401,
            detail={
                "data": None,
                "meta": {
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "timestamp": getattr(request.state, "timestamp", "unknown"),
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


def require_role(allowed_roles: Iterable[str]):
    normalized = {role.upper() for role in allowed_roles}

    def _inner(request: Request) -> None:
        require_authenticated_user(request)
        role = str(getattr(request.state, "user_role", "")).upper()
        if role not in normalized:
            raise HTTPException(
                status_code=403,
                detail={
                    "data": None,
                    "meta": {
                        "request_id": getattr(request.state, "request_id", "unknown"),
                        "timestamp": getattr(request.state, "timestamp", "unknown"),
                        "version": "1.0",
                        "run_id": getattr(request.state, "run_id", None),
                    },
                    "error": {
                        "code": "INSUFFICIENT_PERMISSIONS",
                        "message": "Forbidden",
                        "details": {
                            "required_roles": sorted(normalized),
                            "actual_role": role,
                        },
                    },
                },
            )

    return _inner


def require_same_tenant(request: Request, tenant_id: str) -> None:
    require_authenticated_user(request)
    actor_tenant = str(getattr(request.state, "tenant_id", ""))
    if actor_tenant != str(tenant_id):
        raise HTTPException(
            status_code=403,
            detail={
                "data": None,
                "meta": {
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "timestamp": getattr(request.state, "timestamp", "unknown"),
                    "version": "1.0",
                    "run_id": getattr(request.state, "run_id", None),
                },
                "error": {
                    "code": "TENANT_SCOPE_VIOLATION",
                    "message": "Forbidden",
                    "details": {
                        "actor_tenant_id": actor_tenant,
                        "requested_tenant_id": str(tenant_id),
                    },
                },
            },
        )
