"""Shared queries for CafeScore data."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.cafe_score import CafeScore


async def get_latest_scores_by_cafe_id(
    db: AsyncSession,
    cafe_ids: list[int],
) -> dict[int, CafeScore]:
    """Return the newest CafeScore for each cafe_id."""
    if not cafe_ids:
        return {}

    ranked_scores = (
        select(
            CafeScore,
            func.row_number()
            .over(
                partition_by=CafeScore.cafe_id,
                order_by=(CafeScore.computed_at.desc(), CafeScore.score_id.desc()),
            )
            .label("score_rank"),
        )
        .where(CafeScore.cafe_id.in_(cafe_ids))
        .subquery()
    )
    score = aliased(CafeScore, ranked_scores)
    stmt = select(score).where(ranked_scores.c.score_rank == 1)
    result = await db.execute(stmt)
    scores = result.scalars().all()

    return {score.cafe_id: score for score in scores}
