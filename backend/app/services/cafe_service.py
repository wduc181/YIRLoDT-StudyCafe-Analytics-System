"""
cafe_service.py — Business Logic: Cafe operations.
Mọi DB operation dùng async/await.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.internal.haversine import haversine_distance
from app.models.cafe import Cafe
from app.models.cafe_score import CafeScore
from app.schemas.cafe import CafeResponse
from app.services.cafe_score_service import get_latest_scores_by_cafe_id


def _google_maps_url(cafe: Cafe) -> str:
    return f"https://www.google.com/maps?q={cafe.center_lat},{cafe.center_lng}"


def _build_cafe_response(
    cafe: Cafe,
    score: CafeScore | None,
    distance_meters: float | None = None,
) -> CafeResponse:
    return CafeResponse(
        cafe_id=cafe.cafe_id,
        name=cafe.name,
        address=cafe.address,
        center_lat=cafe.center_lat,
        center_lng=cafe.center_lng,
        radius_meters=cafe.radius_meters,
        behavior_score=score.behavior_score if score else None,
        has_enough_data=score.has_enough_data if score else False,
        distance_meters=round(distance_meters, 2) if distance_meters is not None else None,
        google_maps_url=_google_maps_url(cafe),
    )


async def get_all_cafes(
    db: AsyncSession,
    lat: float | None = None,
    lng: float | None = None,
    radius: int | None = None,
    limit: int = settings.NEARBY_CAFES_DEFAULT_LIMIT,
) -> list[CafeResponse]:
    """Lấy danh sách quán active, hỗ trợ khoảng cách/sort/filter khi có GPS."""
    stmt = select(Cafe).where(Cafe.status == "active")
    result = await db.execute(stmt)
    cafes = result.scalars().all()
    scores_by_cafe_id = await get_latest_scores_by_cafe_id(
        db,
        [cafe.cafe_id for cafe in cafes],
    )

    response = []
    for cafe in cafes:
        score = scores_by_cafe_id.get(cafe.cafe_id)

        distance_meters = None
        if lat is not None and lng is not None:
            distance_meters = haversine_distance(
                lat,
                lng,
                cafe.center_lat,
                cafe.center_lng,
            )
            if radius is not None and distance_meters > radius:
                continue

        response.append(_build_cafe_response(cafe, score, distance_meters))

    if lat is not None and lng is not None:
        response.sort(
            key=lambda cafe: cafe.distance_meters
            if cafe.distance_meters is not None
            else float("inf")
        )

    return response[:limit]
