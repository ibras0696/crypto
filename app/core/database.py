"""Async SQLAlchemy engine and session management for PostgreSQL."""
from __future__ import annotations
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import text
from .config import settings

engine = create_async_engine(settings.database_url, echo=settings.DEBUG, future=True)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def healthcheck_db() -> bool:
    """Simple health check executing SELECT 1."""
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT 1"))
        return result.scalar_one() == 1
