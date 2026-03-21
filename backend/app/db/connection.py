from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    # Use NullPool for test environments (prevents connection leaks)
    poolclass=NullPool if settings.ENVIRONMENT == "test" else None,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager yielding a database session with tenant isolation."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with get_db_session() as session:
        yield session


async def set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """
    Set the PostgreSQL session variable for RLS tenant isolation.
    Bible Rule 4: every DB session must have tenant context set.
    Called once per request, immediately after authentication.
    """
    await session.execute(
        # Use parameterised set_config to prevent injection
        # set_config(setting_name, value, is_local)
        # is_local=TRUE means it resets at end of transaction
        __import__("sqlalchemy").text("SELECT set_config('app.current_tenant_id', :tid, TRUE)"),
        {"tid": tenant_id},
    )
