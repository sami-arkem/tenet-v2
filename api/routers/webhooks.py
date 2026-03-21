from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.webhook_delivery_service import (
    create_webhook,
    delete_webhook,
    dispatch_webhook_delivery,
    get_webhook,
    get_webhook_delivery,
    list_webhook_deliveries,
    list_webhooks,
    queue_webhook_delivery,
    send_test_webhook_delivery,
    update_webhook,
)


class WebhookCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    target_url: str
    secret: str
    event_types: list[str] = Field(min_length=1)


class WebhookUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    target_url: str | None = None
    secret: str | None = None
    event_types: list[str] | None = None
    status: str | None = None


class WebhookQueueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str
    payload: dict


class WebhookResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    webhook_id: str
    name: str
    target_url: str
    secret: str
    event_types: list[str]
    status: str
    consecutive_failures: int
    created_at: str
    updated_at: str
    deterministic_authoritative: bool


class WebhookListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int
    items: list[dict]
    deterministic_authoritative: bool


class WebhookDeliveryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_id: str
    webhook_id: str
    event_type: str
    target_url: str
    status: str
    attempt_count: int
    next_attempt_at: str | None = None
    last_attempt_at: str | None = None
    response_status_code: int | None = None
    failure_reason: str | None = None
    headers: dict
    body: dict
    created_at: str
    updated_at: str
    deterministic_authoritative: bool


class WebhookQueueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str
    delivery_count: int
    deliveries: list[dict]
    deterministic_authoritative: bool


class WebhookDeliveryListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int
    items: list[dict]
    deterministic_authoritative: bool


router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.get("", response_model=Envelope[WebhookListResponse])
def webhooks_list() -> Envelope[WebhookListResponse]:
    try:
        payload = list_webhooks()
        return Envelope[WebhookListResponse](
            data=WebhookListResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"webhook list failed: {exc}") from exc


@router.post("", response_model=Envelope[WebhookResponse])
def webhooks_create(request: WebhookCreateRequest) -> Envelope[WebhookResponse]:
    try:
        payload = create_webhook(
            name=request.name,
            target_url=request.target_url,
            secret=request.secret,
            event_types=request.event_types,
        )
        return Envelope[WebhookResponse](
            data=WebhookResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"webhook create failed: {exc}") from exc


@router.post("/queue", response_model=Envelope[WebhookQueueResponse])
def webhooks_queue(request: WebhookQueueRequest) -> Envelope[WebhookQueueResponse]:
    try:
        payload = queue_webhook_delivery(
            event_type=request.event_type,
            payload=request.payload,
        )
        return Envelope[WebhookQueueResponse](
            data=WebhookQueueResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"webhook queue failed: {exc}") from exc


@router.get("/deliveries", response_model=Envelope[WebhookDeliveryListResponse])
def webhooks_deliveries() -> Envelope[WebhookDeliveryListResponse]:
    try:
        payload = list_webhook_deliveries()
        return Envelope[WebhookDeliveryListResponse](
            data=WebhookDeliveryListResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"webhook delivery list failed: {exc}") from exc


@router.get("/deliveries/{delivery_id}", response_model=Envelope[WebhookDeliveryResponse])
def webhooks_delivery_get(delivery_id: str) -> Envelope[WebhookDeliveryResponse]:
    try:
        payload = get_webhook_delivery(delivery_id=delivery_id)
        return Envelope[WebhookDeliveryResponse](
            data=WebhookDeliveryResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"webhook delivery get failed: {exc}") from exc


@router.post("/deliveries/{delivery_id}/dispatch", response_model=Envelope[WebhookDeliveryResponse])
def webhooks_dispatch(delivery_id: str) -> Envelope[WebhookDeliveryResponse]:
    try:
        payload = dispatch_webhook_delivery(delivery_id=delivery_id)
        return Envelope[WebhookDeliveryResponse](
            data=WebhookDeliveryResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"webhook dispatch failed: {exc}") from exc


@router.get("/{webhook_id}", response_model=Envelope[WebhookResponse])
def webhooks_get(webhook_id: str) -> Envelope[WebhookResponse]:
    try:
        payload = get_webhook(webhook_id=webhook_id)
        return Envelope[WebhookResponse](
            data=WebhookResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"webhook get failed: {exc}") from exc


@router.patch("/{webhook_id}", response_model=Envelope[WebhookResponse])
def webhooks_update(webhook_id: str, request: WebhookUpdateRequest) -> Envelope[WebhookResponse]:
    try:
        payload = update_webhook(
            webhook_id=webhook_id,
            name=request.name,
            target_url=request.target_url,
            secret=request.secret,
            event_types=request.event_types,
            status=request.status,
        )
        return Envelope[WebhookResponse](
            data=WebhookResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"webhook update failed: {exc}") from exc


@router.delete("/{webhook_id}", response_model=Envelope[dict])
def webhooks_delete(webhook_id: str) -> Envelope[dict]:
    try:
        payload = delete_webhook(webhook_id=webhook_id)
        return Envelope[dict](
            data=payload,
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"webhook delete failed: {exc}") from exc


@router.post("/{webhook_id}/test", response_model=Envelope[WebhookDeliveryResponse])
def webhooks_test(webhook_id: str) -> Envelope[WebhookDeliveryResponse]:
    try:
        payload = send_test_webhook_delivery(webhook_id=webhook_id)
        return Envelope[WebhookDeliveryResponse](
            data=WebhookDeliveryResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"webhook test failed: {exc}") from exc
