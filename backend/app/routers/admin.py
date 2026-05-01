"""
admin.py — FastAPI Router: Admin/Internal endpoints.
Endpoints nội bộ, không expose cho end-user.
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.internal import mock_data
from app.schemas.admin import MockDataImportResponse
from app.services.session_service import _run_scoring_background

router = APIRouter(tags=["admin"])


@router.post("/mock-data/import", response_model=MockDataImportResponse)
async def import_mock_data(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Nạp mock data để test pipeline mà không cần đi thực tế."""
    result = await mock_data.import_mock_data(db)
    session_ids = result["session_ids"]

    for session_id in session_ids:
        background_tasks.add_task(_run_scoring_background, session_id)

    return {
        "status": "ok",
        "imported_sessions": result["imported_sessions"],
        "imported_logs": result["imported_logs"],
        "scoring_triggered": len(session_ids),
    }


# [Optional] POST /api/admin/cafes/{cafe_id}/approve — implement sau khi Core hoàn thành
