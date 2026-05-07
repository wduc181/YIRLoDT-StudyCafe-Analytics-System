"""
report.py — FastAPI Router: Report/Export endpoint.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.dependencies import get_db
from app.services import report_service

router = APIRouter(tags=["report"])


def _verify_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    """Protect internal report export without adding full user auth."""
    if not settings.REPORT_EXPORT_TOKEN or x_internal_token != settings.REPORT_EXPORT_TOKEN:
        raise HTTPException(
            status_code=401,
            detail={"status": "error", "message": "unauthorized"},
        )


@router.get("/report/export", dependencies=[Depends(_verify_internal_token)])
async def export_report(db: AsyncSession = Depends(get_db)):
    """Xuất báo cáo nội bộ dưới dạng file Excel."""
    output = await report_service.generate_report(db)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="studycafe_report.xlsx"'
        },
    )
