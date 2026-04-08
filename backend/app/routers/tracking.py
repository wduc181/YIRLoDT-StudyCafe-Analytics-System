"""
tracking.py — FastAPI Router: GPS Tracking endpoint.

Ref: docs/api_design.md mục 5.2.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.tracking import TrackingRequest, TrackingResponse
from app.services import tracking_service

router = APIRouter(tags=["tracking"])


@router.post("/tracking", response_model=TrackingResponse)
async def record_gps(
    request: TrackingRequest,
    db: AsyncSession = Depends(get_db),
):
    """Nhận một điểm GPS từ frontend trong lúc session đang diễn ra."""
    return await tracking_service.record_gps(db, request)
