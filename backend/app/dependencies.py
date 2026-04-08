"""
dependencies.py — FastAPI Dependencies (Dependency Injection).

Tạo dependency get_db() trả về async DB session.
Dùng yield pattern để đảm bảo session được đóng sau mỗi request.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield async DB session, tự đóng sau mỗi request."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
