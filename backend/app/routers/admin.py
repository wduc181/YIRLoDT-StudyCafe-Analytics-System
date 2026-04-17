"""
admin.py — FastAPI Router: Admin/Internal endpoints.
Endpoints nội bộ, không expose cho end-user.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.internal import mock_data

router = APIRouter(tags=["admin"])


@router.post("/mock-data/import")
async def import_mock_data(db: AsyncSession = Depends(get_db)):
    """Nạp mock data để test pipeline mà không cần đi thực tế."""
    result = await mock_data.import_mock_data(db)
    return {
        "status": "ok",
        "imported_sessions": result["imported_sessions"],
        "imported_logs": result["imported_logs"],
    }


# [Optional] POST /api/admin/cafes/{cafe_id}/approve — implement sau khi Core hoàn thành
