"""
report_service.py — Business Logic: Report/Export.

Tổng hợp từ cafe_scores, tạo file Excel (.xlsx) bằng openpyxl.
"""

import io

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cafe import Cafe
from app.services.cafe_score_service import get_latest_scores_by_cafe_id


async def generate_report(db: AsyncSession) -> io.BytesIO:
    """Tổng hợp dữ liệu và tạo file Excel."""
    # Lấy tất cả quán cafe active
    cafe_stmt = select(Cafe).where(Cafe.status == "active")
    cafe_result = await db.execute(cafe_stmt)
    cafes = cafe_result.scalars().all()
    scores_by_cafe_id = await get_latest_scores_by_cafe_id(
        db,
        [cafe.cafe_id for cafe in cafes],
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

        ws.append([
            cafe.cafe_id,
            cafe.name,
            score.total_sessions if score else None,
            score.studying_sessions if score else None,
            score.study_rate if score else None,
            score.avg_stable_duration_min if score else None,
            score.dropoff_rate if score else None,
            score.behavior_score if score else None,
            score.has_enough_data if score else False,
        ])

    # Save to BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
