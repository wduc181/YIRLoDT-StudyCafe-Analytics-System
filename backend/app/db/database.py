"""
database.py — Database Connection và Engine Setup.

Tạo async engine, async_sessionmaker, và Base cho ORM models.
Ref: AGENTS.md mục 3, dùng SQLAlchemy async session + asyncpg.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Async engine từ DATABASE_URL
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

# Async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class cho tất cả ORM models."""
    pass


async def init_db():
    """Tạo tất cả tables (dev only). Dùng Alembic cho production."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Đóng engine connection pool."""
    await engine.dispose()
