"""
cafes.py — FastAPI Router: Cafe endpoints.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.cafe import CafeResponse
from app.services import cafe_service

router = APIRouter(tags=["cafes"])


@router.get("/cafes", response_model=list[CafeResponse])
async def get_cafes(
    lat: float | None = None,
    lng: float | None = None,
    radius: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Lấy danh sách quán cafe + điểm đánh giá, có thể kèm khoảng cách GPS."""
    if (lat is None) != (lng is None):
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "lat and lng must be provided together",
            },
        )

    parsed_radius = None
    if radius is not None:
        try:
            parsed_radius = int(radius)
        except ValueError:
            parsed_radius = None

    if radius is not None and (parsed_radius is None or parsed_radius <= 0):
        return JSONResponse(
            status_code=422,
            content={"status": "error", "message": "invalid radius"},
        )

    return await cafe_service.get_all_cafes(db, lat, lng, parsed_radius, limit)


# [Optional] POST /api/cafes/suggest — tạm stub, implement sau khi Core hoàn thành
