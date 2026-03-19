from __future__ import annotations

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class ApiError(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class ApiMeta(BaseModel):
    request_id: str
    timestamp: str
    version: str = "1.0"
    run_id: Optional[str] = None


class ApiResponse(BaseModel, Generic[T]):
    data: Optional[T] = None
    meta: ApiMeta
    error: Optional[ApiError] = None

    @classmethod
    def success(cls, *, data: T, request_id: str, timestamp: str, run_id: str | None = None) -> "ApiResponse[T]":
        return cls(
            data=data,
            meta=ApiMeta(
                request_id=request_id,
                timestamp=timestamp,
                run_id=run_id,
            ),
            error=None,
        )

    @classmethod
    def failure(
        cls,
        *,
        code: str,
        message: str,
        request_id: str,
        timestamp: str,
        details: dict | None = None,
        run_id: str | None = None,
    ) -> "ApiResponse[None]":
        return cls(
            data=None,
            meta=ApiMeta(
                request_id=request_id,
                timestamp=timestamp,
                run_id=run_id,
            ),
            error=ApiError(
                code=code,
                message=message,
                details=details,
            ),
        )
