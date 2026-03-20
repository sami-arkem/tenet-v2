"""
Entities router — Bible §5.
Regulated entities (AI systems, companies, departments) tracked per tenant.
"""
from __future__ import annotations

import json as _json
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.response import ApiResponse

router = APIRouter()

VALID_ENTITY_TYPES = {"company", "ai_system", "department", "product"}
VALID_COMPANY_SIZES = {"micro", "small", "medium", "large", "enterprise"}


class EntityCreate(BaseModel):
    name: str
    entity_type: str = "company"
    jurisdiction: str = "GB"
    description: Optional[str] = None
    industry_sector: Optional[str] = None
    company_size: Optional[str] = None
    regulatory_regimes: list[str] = []
    metadata: dict[str, Any] = {}


class EntityUpdate(BaseModel):
    name: Optional[str] = None
    entity_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    description: Optional[str] = None
    industry_sector: Optional[str] = None
    company_size: Optional[str] = None
    regulatory_regimes: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


@router.post("", status_code=201)
async def create_entity(
    body: EntityCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if body.entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_ENTITY_TYPE", "message": f"entity_type must be one of: {', '.join(VALID_ENTITY_TYPES)}"},
        )
    if body.company_size and body.company_size not in VALID_COMPANY_SIZES:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_COMPANY_SIZE", "message": f"company_size must be one of: {', '.join(VALID_COMPANY_SIZES)}"},
        )

    entity_id = str(uuid4())
    await db.execute(
        text("""
            INSERT INTO entities
              (id, tenant_id, name, entity_type, jurisdiction,
               description, industry_sector, company_size,
               regulatory_regimes, metadata)
            VALUES
              (:id, current_setting('app.current_tenant_id', TRUE)::uuid,
               :name, :entity_type, :jurisdiction,
               :description, :industry_sector, :company_size,
               :regulatory_regimes, :metadata::jsonb)
        """),
        {
            "id": entity_id,
            "name": body.name,
            "entity_type": body.entity_type,
            "jurisdiction": body.jurisdiction,
            "description": body.description,
            "industry_sector": body.industry_sector,
            "company_size": body.company_size,
            "regulatory_regimes": body.regulatory_regimes,
            "metadata": _json.dumps(body.metadata),
        },
    )
    await db.commit()
    return ApiResponse.success(data={"id": entity_id, "name": body.name}).model_dump()


@router.get("")
async def list_entities(
    jurisdiction: Optional[str] = None,
    entity_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict:
    conditions = ["tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid"]
    params: dict = {"limit": limit, "offset": offset}

    if jurisdiction:
        conditions.append("jurisdiction = :jurisdiction")
        params["jurisdiction"] = jurisdiction
    if entity_type:
        conditions.append("entity_type = :entity_type")
        params["entity_type"] = entity_type
    if is_active is not None:
        conditions.append("is_active = :is_active")
        params["is_active"] = is_active

    where = " AND ".join(conditions)
    rows = await db.execute(
        text(f"""
            SELECT id, name, entity_type, jurisdiction, description,
                   industry_sector, company_size, regulatory_regimes,
                   metadata, is_active, created_at, updated_at
            FROM entities
            WHERE {where}
            ORDER BY name ASC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    count_row = await db.execute(
        text(f"SELECT COUNT(*) FROM entities WHERE {where}"),
        params,
    )
    total = count_row.scalar() or 0
    items = [dict(r) for r in rows.mappings()]
    return ApiResponse.success(
        data={"items": items, "total": total, "limit": limit, "offset": offset}
    ).model_dump()


@router.get("/{entity_id}")
async def get_entity(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await db.execute(
        text("""
            SELECT id, name, entity_type, jurisdiction, description,
                   industry_sector, company_size, regulatory_regimes,
                   metadata, is_active, created_at, updated_at
            FROM entities
            WHERE id = :id
              AND tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
        """),
        {"id": entity_id},
    )
    item = row.mappings().fetchone()
    if not item:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Entity not found"})
    return ApiResponse.success(data=dict(item)).model_dump()


@router.patch("/{entity_id}")
async def update_entity(
    entity_id: str,
    body: EntityUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    updates: list[str] = ["updated_at = now()"]
    params: dict = {"id": entity_id}

    data = body.model_dump(exclude_none=True)
    for field, value in data.items():
        if field == "metadata":
            updates.append("metadata = :metadata::jsonb")
            params["metadata"] = _json.dumps(value)
        elif field == "regulatory_regimes":
            updates.append(f"regulatory_regimes = :{field}")
            params[field] = value
        else:
            updates.append(f"{field} = :{field}")
            params[field] = value

    if len(updates) == 1:  # only updated_at
        raise HTTPException(status_code=422, detail={"code": "NO_FIELDS", "message": "No fields to update"})

    row = await db.execute(
        text(f"""
            UPDATE entities
            SET {', '.join(updates)}
            WHERE id = :id
              AND tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
            RETURNING id, name, entity_type, jurisdiction, is_active
        """),
        params,
    )
    updated = row.mappings().fetchone()
    if not updated:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Entity not found"})
    await db.commit()
    return ApiResponse.success(data=dict(updated)).model_dump()


@router.delete("/{entity_id}")
async def delete_entity(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await db.execute(
        text("""
            UPDATE entities SET is_active = FALSE, updated_at = now()
            WHERE id = :id
              AND tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
            RETURNING id
        """),
        {"id": entity_id},
    )
    if not row.fetchone():
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Entity not found"})
    await db.commit()
    return ApiResponse.success(data={"deleted": True}).model_dump()
