"""
Auth router — Bible §4.3.
POST /v1/auth/login  → JWT token
POST /v1/auth/signup → create user + JWT
POST /v1/auth/refresh → new token from refresh token
POST /v1/auth/logout  → invalidate session
GET  /v1/auth/me      → current user profile
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.schemas.response import ApiResponse

router = APIRouter()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Schemas ──────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12)
    full_name: str = Field(..., min_length=1, max_length=200)
    tenant_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    tenant_id: str
    role: str


class UserProfile(BaseModel):
    user_id: str
    tenant_id: str
    email: str
    full_name: str
    role: str
    created_at: datetime


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def _validate_password_strength(password: str) -> list[str]:
    errors = []
    if len(password) < 12:
        errors.append("At least 12 characters required")
    if not any(c.isupper() for c in password):
        errors.append("At least one uppercase letter required")
    if not any(c.islower() for c in password):
        errors.append("At least one lowercase letter required")
    if not any(c.isdigit() for c in password):
        errors.append("At least one number required")
    if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in password):
        errors.append("At least one special character required")
    return errors


def _create_token(user_id: str, tenant_id: str, role: str) -> tuple[str, int]:
    expires_in = settings.JWT_EXPIRY_HOURS * 3600
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid4()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, expires_in


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/signup", status_code=201)
async def signup(
    body: SignupRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Validate password strength
    errors = _validate_password_strength(body.password)
    if errors:
        raise HTTPException(
            status_code=422,
            detail={"code": "PASSWORD_TOO_WEAK", "message": "; ".join(errors), "requirements": errors},
        )

    # Check email not taken
    row = await db.execute(
        text("SELECT id FROM users WHERE email = :email LIMIT 1"),
        {"email": body.email.lower()},
    )
    if row.fetchone():
        raise HTTPException(
            status_code=409,
            detail={"code": "EMAIL_TAKEN", "message": "An account with this email already exists"},
        )

    # Create tenant (if new signup)
    tenant_id = str(uuid4())
    tenant_name = body.tenant_name or f"{body.full_name.split()[0]}'s Workspace"
    tenant_slug = tenant_name.lower().replace(" ", "-").replace("'", "")[:50]

    await db.execute(
        text("""
            INSERT INTO tenants (id, name, slug, plan)
            VALUES (:id, :name, :slug, 'starter')
        """),
        {"id": tenant_id, "name": tenant_name, "slug": tenant_slug},
    )

    # Create user
    user_id = str(uuid4())
    pw_hash = _hash_password(body.password)

    await db.execute(
        text("""
            INSERT INTO users (id, tenant_id, email, full_name, role, password_hash)
            VALUES (:id, :tenant_id, :email, :full_name, 'owner', :pw_hash)
        """),
        {
            "id": user_id,
            "tenant_id": tenant_id,
            "email": body.email.lower(),
            "full_name": body.full_name,
            "pw_hash": pw_hash,
        },
    )

    await db.commit()

    token, expires_in = _create_token(user_id, tenant_id, "owner")

    return ApiResponse.success(
        data=TokenResponse(
            access_token=token,
            expires_in=expires_in,
            user_id=user_id,
            tenant_id=tenant_id,
            role="owner",
        ).model_dump(),
    ).model_dump()


@router.post("/login")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await db.execute(
        text("""
            SELECT id, tenant_id, role, password_hash, is_suspended
            FROM users WHERE email = :email LIMIT 1
        """),
        {"email": body.email.lower()},
    )
    user = row.mappings().fetchone()

    # Always verify (prevent timing attacks)
    stored_hash = user["password_hash"] if user else pwd_ctx.hash("dummy-never-matches")
    valid = _verify_password(body.password, stored_hash)

    if not user or not valid:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password"},
        )

    if user["is_suspended"]:
        raise HTTPException(
            status_code=403,
            detail={"code": "ACCOUNT_SUSPENDED", "message": "Your account has been suspended"},
        )

    token, expires_in = _create_token(str(user["id"]), str(user["tenant_id"]), user["role"])

    return ApiResponse.success(
        data=TokenResponse(
            access_token=token,
            expires_in=expires_in,
            user_id=str(user["id"]),
            tenant_id=str(user["tenant_id"]),
            role=user["role"],
        ).model_dump(),
    ).model_dump()


@router.get("/me")
async def me(
    db: AsyncSession = Depends(get_db),
    # Will be populated by auth middleware
) -> dict:
    # This endpoint is hit post-auth-middleware; request.state has user info.
    # For now return a placeholder (middleware sets state.user)
    raise HTTPException(status_code=501, detail={"code": "NOT_IMPLEMENTED", "message": "Use /v1/auth/login"})


@router.post("/logout")
async def logout() -> dict:
    # Stateless JWT — client discards token. If we want server-side revocation,
    # add token jti to a blocklist table. For now, no-op.
    return ApiResponse.success(data={"logged_out": True}).model_dump()
