"""
report_service.py — Business Logic: Report/Export.

Tổng hợp từ cafe_scores, tạo file Excel (.xlsx) bằng openpyxl.
"""

import io

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cafe import Cafe
from app.models.cafe_score import CafeScore


async def generate_report(db: AsyncSession) -> io.BytesIO:
    """Tổng hợp dữ liệu và tạo file Excel."""
    # Lấy tất cả quán cafe active
    cafe_stmt = select(Cafe).where(Cafe.status == "active")
    cafe_result = await db.execute(cafe_stmt)
    cafes = cafe_result.scalars().all()

    # Tạo workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "StudyCafe Report"

    # Header
    headers = [
        "Cafe ID", "Tên quán", "Tổng lượt đến",
        "Thời gian trung bình (phút)", "Tỷ lệ rời sớm",
        "Điểm hành vi", "Đủ dữ liệu",
    ]
    ws.append(headers)

    # Data rows
    for cafe in cafes:
        score_stmt = (
            select(CafeScore)
            .where(CafeScore.cafe_id == cafe.cafe_id)
            .order_by(CafeScore.computed_at.desc())
            .limit(1)
        )
        score_result = await db.execute(score_stmt)
        score = score_result.scalar_one_or_none()

        ws.append([
            cafe.cafe_id,
            cafe.name,
            score.total_visits if score else None,
            score.avg_duration if score else None,
            score.dropoff_rate if score else None,
            score.behavior_score if score else None,
            score.has_enough_data if score else False,
        ])

    # Save to BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
