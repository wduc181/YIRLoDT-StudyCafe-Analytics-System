"""
report.py — FastAPI Router: Report/Export endpoint.

Ref: docs/api_design.md mục 5.6.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services import report_service

router = APIRouter(tags=["report"])


@router.get("/report/export")
async def export_report(db: AsyncSession = Depends(get_db)):
    """Xuất báo cáo tổng hợp dưới dạng file Excel."""
    output = await report_service.generate_report(db)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="studycafe_report.xlsx"'
        },
    )
