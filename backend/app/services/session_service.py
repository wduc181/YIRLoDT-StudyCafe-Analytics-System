"""
session_service.py — Business Logic: Session operations.

Mọi DB operation dùng async/await.
Ref: docs/api_design.md mục 5.1, 5.3, 5.5.
"""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.models.gps_log import GpsLog
from app.schemas.session import (
    SessionStartRequest,
    SessionStartResponse,
    SessionEndRequest,
    SessionEndResponse,
    SessionResponse,
)


async def start_session(
    db: AsyncSession, data: SessionStartRequest
) -> SessionStartResponse:
    """Tạo session mới với UUID, status='active'."""
    now = datetime.now(timezone.utc)
    session = Session(
        session_id=uuid.uuid4(),
        device_id=data.device_id,
        cafe_id=data.cafe_id,
        start_time=now,
        status="active",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return SessionStartResponse(
        status="ok",
        session_id=str(session.session_id),
        started_at=session.start_time,
    )


async def end_session(
    db: AsyncSession, data: SessionEndRequest
) -> SessionEndResponse:
    """Cập nhật end_time, tính duration_min, status='completed'."""
    stmt = select(Session).where(
        Session.session_id == uuid.UUID(data.session_id)
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "message": "session not found"},
        )

    now = datetime.now(timezone.utc)
    duration = (now - session.start_time).total_seconds() / 60.0

    session.end_time = now
    session.duration_min = round(duration, 1)
    session.status = "completed"
    await db.commit()

    # TODO: Trigger scoring_service sau khi kết thúc session
    # Chờ Scoring team chốt real-time hay batch

    return SessionEndResponse(
        status="ok",
        session_id=str(session.session_id),
        ended_at=session.end_time,
        duration_min=session.duration_min,
    )


async def get_session(db: AsyncSession, session_id: str) -> SessionResponse:
    """Lấy chi tiết session + gps_log_count."""
    stmt = select(Session).where(
        Session.session_id == uuid.UUID(session_id)
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "message": "session not found"},
        )

    # Đếm GPS logs
    count_stmt = (
        select(func.count())
        .select_from(GpsLog)
        .where(GpsLog.session_id == session.session_id)
    )
    count_result = await db.execute(count_stmt)
    gps_count = count_result.scalar() or 0

    return SessionResponse(
        session_id=str(session.session_id),
        device_id=session.device_id,
        cafe_id=session.cafe_id,
        start_time=session.start_time,
        end_time=session.end_time,
        duration_min=session.duration_min,
        gps_log_count=gps_count,
        status=session.status,
    )
