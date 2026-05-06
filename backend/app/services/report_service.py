"""
report_service.py — Business Logic: Report/Export.

Tổng hợp từ cafe_scores, tạo file Excel (.xlsx) bằng openpyxl.
"""

import io

from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cafe import Cafe
from app.models.session_result import SessionResult
from app.services.cafe_score_service import get_latest_scores_by_cafe_id


async def _get_avg_stable_duration_by_cafe_id(
    db: AsyncSession,
    cafe_ids: list[int],
) -> dict[int, float]:
    """Return average stable duration from persisted studying session results."""
    if not cafe_ids:
        return {}

    stmt = (
        select(
            SessionResult.cafe_id,
            func.avg(SessionResult.stable_duration_min).label(
                "avg_stable_duration_min"
            ),
        )
        .where(
            SessionResult.cafe_id.in_(cafe_ids),
            SessionResult.is_studying.is_(True),
            SessionResult.stable_duration_min.is_not(None),
        )
        .group_by(SessionResult.cafe_id)
    )
    result = await db.execute(stmt)

    return {
        cafe_id: round(float(avg_stable_duration_min), 1)
        for cafe_id, avg_stable_duration_min in result.all()
        if cafe_id is not None and avg_stable_duration_min is not None
    }


async def generate_report(db: AsyncSession) -> io.BytesIO:
    """Tổng hợp dữ liệu và tạo file Excel."""
    # Lấy tất cả quán cafe active
    cafe_stmt = select(Cafe).where(Cafe.status == "active")
    cafe_result = await db.execute(cafe_stmt)
    cafes = cafe_result.scalars().all()
    cafe_ids = [cafe.cafe_id for cafe in cafes]
    scores_by_cafe_id = await get_latest_scores_by_cafe_id(
        db,
        cafe_ids,
    )
    avg_stable_duration_by_cafe_id = await _get_avg_stable_duration_by_cafe_id(
        db,
        cafe_ids,
    )

    # Tạo workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "StudyCafe Report"

    # Header — khớp CafeScore Bayesian schema (api_design.md mục 8.4)
    headers = [
        "Cafe ID", "Tên quán", "Tổng sessions",
        "Sessions học tập", "Tỷ lệ học tập",
        "TG ổn định TB (phút)", "Tỷ lệ rời sớm",
        "Điểm hành vi", "Đủ dữ liệu",
    ]
    ws.append(headers)

    # Data rows
    for cafe in cafes:
        score = scores_by_cafe_id.get(cafe.cafe_id)
        avg_stable_duration_min = (
            score.avg_stable_duration_min
            if score and score.avg_stable_duration_min is not None
            else avg_stable_duration_by_cafe_id.get(cafe.cafe_id)
        )

        ws.append([
            cafe.cafe_id,
            cafe.name,
            score.total_sessions if score else None,
            score.studying_sessions if score else None,
            score.study_rate if score else None,
            avg_stable_duration_min,
            score.dropoff_rate if score else None,
            score.behavior_score if score else None,
            score.has_enough_data if score else False,
        ])

    # Save to BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
