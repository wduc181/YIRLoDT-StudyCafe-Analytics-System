"""
tracking_service.py — Business Logic: GPS Tracking.

Chống duplicate bằng ON CONFLICT (session_id, timestamp) DO NOTHING.
Ref: docs/api_design.md mục 5.2.
"""

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.models.gps_log import GpsLog
from app.schemas.tracking import TrackingRequest, TrackingResponse


async def record_gps(db: AsyncSession, data: TrackingRequest) -> TrackingResponse:
    """Lưu GPS log vào DB với duplicate prevention."""
    # Validate session_id tồn tại và đang active
    session_uuid = uuid.UUID(data.session_id)
    stmt = select(Session).where(Session.session_id == session_uuid)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "message": "session not found"},
        )

    # Insert GPS log với ON CONFLICT DO NOTHING
    insert_stmt = pg_insert(GpsLog).values(
        session_id=session_uuid,
        device_id=data.device_id,
        lat=data.lat,
        lng=data.lng,
        accuracy_m=data.accuracy,
        timestamp=data.timestamp,
        is_noise=False,
    )
    insert_stmt = insert_stmt.on_conflict_do_nothing(
        constraint="uq_gps_session_timestamp"
    )
    insert_stmt = insert_stmt.returning(GpsLog.log_id)

    result = await db.execute(insert_stmt)
    await db.commit()

    row = result.fetchone()
    if row is None:
        # Duplicate — log đã tồn tại, trả lại log_id hiện có
        existing_stmt = select(GpsLog.log_id).where(
            GpsLog.session_id == session_uuid,
            GpsLog.timestamp == data.timestamp,
        )
        existing_result = await db.execute(existing_stmt)
        existing_row = existing_result.fetchone()
        log_id = existing_row[0] if existing_row else 0
    else:
        log_id = row[0]

    # TODO: Nếu GPS đầu tiên và session chưa có cafe_id,
    # gọi geo_resolver.resolve_nearest_cafe() để cập nhật session.cafe_id

    return TrackingResponse(status="ok", log_id=log_id)
