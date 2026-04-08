"""
cafes.py — FastAPI Router: Cafe endpoints.

Ref: docs/api_design.md mục 5.4, 5.8, 5.9.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.cafe import CafeResponse
from app.services import cafe_service

router = APIRouter(tags=["cafes"])


@router.get("/cafes", response_model=list[CafeResponse])
async def get_cafes(db: AsyncSession = Depends(get_db)):
    """Lấy danh sách quán cafe + điểm đánh giá hiện tại."""
    return await cafe_service.get_all_cafes(db)


# [Optional] GET /api/cafes/nearby — tạm stub, implement sau khi Core hoàn thành
# [Optional] POST /api/cafes/suggest — tạm stub, implement sau khi Core hoàn thành
