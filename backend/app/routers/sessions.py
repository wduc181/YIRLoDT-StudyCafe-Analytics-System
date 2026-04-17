"""
sessions.py — FastAPI Router: Session endpoints.
Error format: {"status": "error", "message": "..."}.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.session import (
    SessionStartRequest,
    SessionStartResponse,
    SessionEndRequest,
    SessionEndResponse,
    SessionResponse,
)
from app.services import session_service

router = APIRouter(tags=["sessions"])


@router.post("/session/start", response_model=SessionStartResponse)
async def start_session(
    request: SessionStartRequest,
    db: AsyncSession = Depends(get_db),
):
    """Tạo một session mới khi người dùng bắt đầu học."""
    if not request.device_id:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "device_id is required"},
        )
    return await session_service.start_session(db, request)


@router.post("/session/end", response_model=SessionEndResponse)
async def end_session(
    request: SessionEndRequest,
    db: AsyncSession = Depends(get_db),
):
    """Kết thúc session và trigger pipeline scoring nếu cần."""
    return await session_service.end_session(db, request)


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Lấy chi tiết session để debug hoặc kiểm tra."""
    return await session_service.get_session(db, session_id)
