"""
Tenant context middleware — sets PostgreSQL session variable for RLS.
Bible Rule 4: every DB session must have tenant context set.
"""
from __future__ import annotations

from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Any, call_next: Any) -> Any:
        # Tenant context is set inside each route via set_tenant_context(db, tenant_id)
        # This middleware exists as the future hook for Supabase JWT passthrough.
        return await call_next(request)
