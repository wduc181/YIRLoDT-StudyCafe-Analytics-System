"""
session_service.py — Business Logic: Session operations.
Mọi DB operation dùng async/await.
"""

import uuid
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException
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

logger = logging.getLogger(__name__)


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


async def _run_scoring_background(session_id: str) -> None:
    """
    Background task: chạy scoring với DB session riêng.

    Tạo AsyncSession mới vì session của request đã bị close
    sau khi response trả về. Không reuse db từ endpoint.
    """
    from app.db.database import async_session
    from app.services.scoring_service import score_and_update_cafe

    async with async_session() as db:
        try:
            result = await score_and_update_cafe(db, session_id)
            logger.info(
                "Scoring background result for session %s: %s",
                session_id,
                result.get("status"),
            )
        except Exception:
            logger.exception("Scoring background failed for session %s", session_id)


async def end_session(
    db: AsyncSession,
    data: SessionEndRequest,
    background_tasks: BackgroundTasks,
) -> SessionEndResponse:
    """Cập nhật end_time, tính duration_min, status='completed'."""
    stmt = select(Session).where(
        Session.session_id == data.session_id
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "message": "session not found"},
        )

    if session.status == "completed":
        # Idempotent: session đã kết thúc trước đó → trả lại kết quả hiện có.
        # Re-trigger scoring background để recovery nếu task lần đầu chưa chạy.
        background_tasks.add_task(_run_scoring_background, str(data.session_id))
        return SessionEndResponse(
            status="ok",
            session_id=str(session.session_id),
            ended_at=session.end_time,
            duration_min=session.duration_min,
        )

    now = datetime.now(timezone.utc)
    duration = (now - session.start_time).total_seconds() / 60.0

    session.end_time = now
    session.duration_min = round(duration, 1)
    session.status = "completed"
    await db.commit()

    # Trigger scoring engine trong background (non-blocking)
    # Dùng DB session riêng — session của request sẽ bị close sau response
    background_tasks.add_task(_run_scoring_background, str(data.session_id))

    return SessionEndResponse(
        status="ok",
        session_id=str(session.session_id),
        ended_at=session.end_time,
        duration_min=session.duration_min,
    )


async def get_session(db: AsyncSession, session_id: UUID) -> SessionResponse:
    """Lấy chi tiết session + gps_log_count."""
    stmt = select(Session).where(
        Session.session_id == session_id
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
