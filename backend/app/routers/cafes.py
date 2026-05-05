"""
cafes.py — FastAPI Router: Cafe endpoints.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.dependencies import get_db
from app.schemas.cafe import CafeListResponse
from app.services import cafe_service

router = APIRouter(tags=["cafes"])


def _parse_radius_param(value: str | None, message: str) -> int | None | JSONResponse:
    if value is None:
        return None

    try:
        parsed_value = int(value)
    except ValueError:
        parsed_value = None

    if parsed_value is None or parsed_value <= 0:
        return JSONResponse(
            status_code=422,
            content={"status": "error", "message": message},
        )

    return parsed_value


@router.get("/cafes", response_model=CafeListResponse)
async def get_cafes(
    lat: float | None = None,
    lng: float | None = None,
    radius: str | None = None,
    min_radius: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=settings.NEARBY_CAFES_DEFAULT_LIMIT, ge=1, le=50),
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

    parsed_radius = _parse_radius_param(radius, "invalid radius")
    if isinstance(parsed_radius, JSONResponse):
        return parsed_radius

    parsed_min_radius = _parse_radius_param(min_radius, "invalid min_radius")
    if isinstance(parsed_min_radius, JSONResponse):
        return parsed_min_radius

    if (
        parsed_radius is not None
        and parsed_min_radius is not None
        and parsed_min_radius >= parsed_radius
    ):
        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "message": "min_radius must be smaller than radius",
            },
        )

    return await cafe_service.get_all_cafes(
        db,
        lat,
        lng,
        parsed_radius,
        parsed_min_radius,
        page,
        limit,
    )


# [Optional] POST /api/cafes/suggest — tạm stub, implement sau khi Core hoàn thành
