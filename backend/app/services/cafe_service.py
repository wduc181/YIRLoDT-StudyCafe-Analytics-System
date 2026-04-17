"""
cafe_service.py — Business Logic: Cafe operations.
Mọi DB operation dùng async/await.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cafe import Cafe
from app.models.cafe_score import CafeScore
from app.schemas.cafe import CafeResponse


async def get_all_cafes(db: AsyncSession) -> list[CafeResponse]:
    """Lấy danh sách quán (status='active') kèm score mới nhất."""
    stmt = select(Cafe).where(Cafe.status == "active")
    result = await db.execute(stmt)
    cafes = result.scalars().all()

    response = []
    for cafe in cafes:
        # Lấy score mới nhất cho quán này
        score_stmt = (
            select(CafeScore)
            .where(CafeScore.cafe_id == cafe.cafe_id)
            .order_by(CafeScore.computed_at.desc())
            .limit(1)
        )
        score_result = await db.execute(score_stmt)
        score = score_result.scalar_one_or_none()

        response.append(
            CafeResponse(
                cafe_id=cafe.cafe_id,
                name=cafe.name,
                address=cafe.address,
                center_lat=cafe.center_lat,
                center_lng=cafe.center_lng,
                radius_meters=cafe.radius_meters,
                behavior_score=score.behavior_score if score else None,
                has_enough_data=score.has_enough_data if score else False,
            )
        )

    return response
