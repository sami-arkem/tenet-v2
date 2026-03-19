from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.notification_outbox_service import (
    dispatch_notification,
    get_notification,
    list_notifications,
    queue_notification_event,
    queue_regulatory_alert_notification,
)


class QueueNotificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str
    payload: dict
    recipients: list[dict]
    channels: list[str] | None = None


class QueueRegulatoryAlertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_payload: dict
    recipients: list[dict]


class NotificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notification_id: str
    event_type: str | None = None
    payload: dict | None = None
    subject: str | None = None
    body: str | None = None
    status: str
    deliveries: list[dict]
    created_at: str | None = None
    updated_at: str | None = None
    deterministic_authoritative: bool


class NotificationDispatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notification_id: str
    status: str
    sent_count: int
    failed_count: int
    skipped_count: int
    deliveries: list[dict]
    deterministic_authoritative: bool


class NotificationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int
    items: list[dict]
    deterministic_authoritative: bool


router = APIRouter(prefix="/v1/notifications", tags=["notifications"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.post("/queue", response_model=Envelope[NotificationResponse])
def notifications_queue(request: QueueNotificationRequest) -> Envelope[NotificationResponse]:
    try:
        payload = queue_notification_event(
            event_type=request.event_type,
            payload=request.payload,
            recipients=request.recipients,
            channels=request.channels,
        )
        return Envelope[NotificationResponse](
            data=NotificationResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"notification queue failed: {exc}") from exc


@router.post("/queue/regulatory-alert", response_model=Envelope[NotificationResponse])
def notifications_queue_regulatory_alert(request: QueueRegulatoryAlertRequest) -> Envelope[NotificationResponse]:
    try:
        payload = queue_regulatory_alert_notification(
            alert_payload=request.alert_payload,
            recipients=request.recipients,
        )
        return Envelope[NotificationResponse](
            data=NotificationResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"regulatory alert queue failed: {exc}") from exc


@router.post("/{notification_id}/dispatch", response_model=Envelope[NotificationDispatchResponse])
def notifications_dispatch(notification_id: str) -> Envelope[NotificationDispatchResponse]:
    try:
        payload = dispatch_notification(notification_id=notification_id)
        return Envelope[NotificationDispatchResponse](
            data=NotificationDispatchResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"notification dispatch failed: {exc}") from exc


@router.get("", response_model=Envelope[NotificationListResponse])
def notifications_list() -> Envelope[NotificationListResponse]:
    try:
        payload = list_notifications()
        return Envelope[NotificationListResponse](
            data=NotificationListResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"notification list failed: {exc}") from exc


@router.get("/{notification_id}", response_model=Envelope[NotificationResponse])
def notifications_get(notification_id: str) -> Envelope[NotificationResponse]:
    try:
        payload = get_notification(notification_id=notification_id)
        return Envelope[NotificationResponse](
            data=NotificationResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"notification lookup failed: {exc}") from exc
