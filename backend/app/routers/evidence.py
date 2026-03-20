"""
Evidence router — Bible §7.
POST /v1/evidence/upload      → upload file, queue processing
GET  /v1/evidence             → list tenant's evidence
GET  /v1/evidence/{item_id}   → get single evidence item
DELETE /v1/evidence/{item_id} → soft-delete (mark status=DELETED)
GET  /v1/evidence/{item_id}/download → presigned URL
"""
from __future__ import annotations

import hashlib
import os
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db, set_tenant_context
from app.schemas.response import ApiResponse

router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "application/json",
    "text/plain",
}

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv", ".json", ".txt"}


def _ext(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


@router.post("/upload", status_code=201)
async def upload_evidence(
    file: UploadFile = File(...),
    entity_id: Optional[str] = Form(None),
    audit_run_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from fastapi import Request
    # tenant_id / user_id come from middleware (set on request.state)
    # We reference them via db context already set by TenantMiddleware

    # Validate extension
    if _ext(file.filename or "") not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_FILE_TYPE", "message": f"File type not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"},
        )

    # Validate MIME type
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_MIME_TYPE", "message": "File content type not supported"},
        )

    # Read file (enforce 50 MB limit)
    contents = await file.read()
    if len(contents) > settings.MAX_EVIDENCE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail={"code": "FILE_TOO_LARGE", "message": "File too large. Maximum 50 MB."},
        )

    # Compute SHA-256
    file_hash = hashlib.sha256(contents).hexdigest()

    # Store file locally (or S3/supabase in production)
    upload_dir = os.path.join(settings.STORAGE_LOCAL_ROOT, "evidence")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{file_hash}{_ext(file.filename or '')}")
    if not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            f.write(contents)

    item_id = str(uuid4())
    file_size = len(contents)

    await db.execute(
        text("""
            INSERT INTO evidence_items
              (id, tenant_id, entity_id, audit_run_id, original_name,
               file_hash, file_size_bytes, mime_type, storage_path, status)
            VALUES
              (:id, current_setting('app.current_tenant_id', TRUE), :entity_id, :audit_run_id,
               :original_name, :file_hash, :file_size, :mime_type, :storage_path, 'PROCESSING')
        """),
        {
            "id": item_id,
            "entity_id": entity_id,
            "audit_run_id": audit_run_id,
            "original_name": file.filename,
            "file_hash": file_hash,
            "file_size": file_size,
            "mime_type": file.content_type or "application/octet-stream",
            "storage_path": file_path,
        },
    )
    await db.commit()

    # Run synchronous classification pipeline (Bible §7)
    from app.agents.evidence_agent import classify_evidence
    mime = file.content_type or "application/octet-stream"
    clf = classify_evidence(file_path, mime)

    await db.execute(
        text("""
            UPDATE evidence_items
            SET status = CASE WHEN :is_empty THEN 'EMPTY' ELSE 'READY' END,
                document_type = :doc_type,
                classification_confidence = :confidence,
                extracted_text = :extracted_text
            WHERE id = :id
        """),
        {
            "id": item_id,
            "is_empty": clf.is_empty,
            "doc_type": clf.document_type.value,
            "confidence": clf.confidence_score,
            "extracted_text": clf.extracted_text,
        },
    )
    await db.commit()

    return ApiResponse.success(
        data={
            "id": item_id,
            "original_name": file.filename,
            "file_hash": file_hash,
            "file_size_bytes": file_size,
            "status": "EMPTY" if clf.is_empty else "READY",
            "document_type": clf.document_type.value,
            "classification_confidence": clf.confidence.value,
            "word_count": clf.word_count,
        }
    ).model_dump()


@router.get("")
async def list_evidence(
    audit_run_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict:
    conditions = ["tenant_id = current_setting('app.current_tenant_id', TRUE)"]
    params: dict = {"limit": limit, "offset": offset}

    if audit_run_id:
        conditions.append("audit_run_id = :audit_run_id")
        params["audit_run_id"] = audit_run_id
    if status:
        conditions.append("status = :status")
        params["status"] = status.upper()

    where = " AND ".join(conditions)

    rows = await db.execute(
        text(f"""
            SELECT id, original_name, file_hash, file_size_bytes, mime_type,
                   status, document_type, classification_confidence,
                   created_at, audit_run_id, entity_id
            FROM evidence_items
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )

    count_row = await db.execute(
        text(f"SELECT COUNT(*) FROM evidence_items WHERE {where}"),
        params,
    )
    total = count_row.scalar() or 0

    items = [dict(r) for r in rows.mappings()]
    return ApiResponse.success(
        data={"items": items, "total": total, "limit": limit, "offset": offset}
    ).model_dump()


@router.get("/{item_id}")
async def get_evidence_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await db.execute(
        text("""
            SELECT id, tenant_id, original_name, file_hash, file_size_bytes,
                   mime_type, status, document_type, classification_confidence,
                   created_at, audit_run_id, entity_id, storage_path
            FROM evidence_items
            WHERE id = :id
              AND tenant_id = current_setting('app.current_tenant_id', TRUE)
        """),
        {"id": item_id},
    )
    item = row.mappings().fetchone()
    if not item:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Evidence item not found"})

    return ApiResponse.success(data=dict(item)).model_dump()


@router.get("/{item_id}/download")
async def get_download_url(
    item_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await db.execute(
        text("""
            SELECT storage_path, original_name, mime_type
            FROM evidence_items
            WHERE id = :id
              AND tenant_id = current_setting('app.current_tenant_id', TRUE)
        """),
        {"id": item_id},
    )
    item = row.mappings().fetchone()
    if not item:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Evidence item not found"})

    # In production: generate presigned S3/Supabase URL (1hr expiry)
    # For local: return the file path as a direct endpoint
    return ApiResponse.success(
        data={
            "url": f"/v1/evidence/{item_id}/file",
            "expires_in": 3600,
            "filename": item["original_name"],
            "mime_type": item["mime_type"],
        }
    ).model_dump()


@router.delete("/{item_id}", status_code=200)
async def delete_evidence_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await db.execute(
        text("""
            UPDATE evidence_items SET status='DELETED'
            WHERE id = :id
              AND tenant_id = current_setting('app.current_tenant_id', TRUE)
            RETURNING id
        """),
        {"id": item_id},
    )
    if not row.fetchone():
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Evidence item not found"})

    await db.commit()
    return ApiResponse.success(data={"deleted": True}).model_dump()
