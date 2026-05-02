"""
admin.py — FastAPI Router: Admin/Internal endpoints.
Endpoints nội bộ, không expose cho end-user.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.internal import mock_data
from app.schemas.admin import MockDataImportResponse
from app.services.scoring_service import score_and_update_cafe

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


@router.post("/mock-data/import", response_model=MockDataImportResponse)
async def import_mock_data(
    db: AsyncSession = Depends(get_db),
):
    """Nạp mock data và chạy scoring synchronously để demo dataset sẵn sàng."""
    result = await mock_data.import_mock_data(db)
    session_ids = result["session_ids"]

    # Scoring chạy đồng bộ: đảm bảo cafe scores tồn tại khi response trả về.
    # Cần thiết cho demo flow — user mở cafe list ngay sau import phải thấy rating.
    scored_count = 0
    for session_id in session_ids:
        try:
            score_result = await score_and_update_cafe(db, session_id)
            if score_result.get("status") == "ok":
                scored_count += 1
        except Exception:
            logger.exception("Scoring failed for session %s", session_id)

    return {
        "status": "ok",
        "imported_sessions": result["imported_sessions"],
        "imported_logs": result["imported_logs"],
        "scoring_triggered": scored_count,
    }


# [Optional] POST /api/admin/cafes/{cafe_id}/approve — implement sau khi Core hoàn thành
