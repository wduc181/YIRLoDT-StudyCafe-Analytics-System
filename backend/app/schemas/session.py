"""
session.py — Pydantic Schemas cho Session domain.

Ref: docs/api_design.md mục 5.1, 5.3, 5.5.
"""

from datetime import datetime

from pydantic import BaseModel


class SessionStartRequest(BaseModel):
    """Request body cho POST /api/session/start."""
    device_id: str
    cafe_id: int | None = None


class SessionStartResponse(BaseModel):
    """Response cho POST /api/session/start."""
    status: str = "ok"
    session_id: str
    started_at: datetime


class SessionEndRequest(BaseModel):
    """Request body cho POST /api/session/end."""
    session_id: str


class SessionEndResponse(BaseModel):
    """Response cho POST /api/session/end."""
    status: str = "ok"
    session_id: str
    ended_at: datetime
    duration_min: float


class SessionResponse(BaseModel):
    """Response cho GET /api/session/{session_id}."""
    session_id: str
    device_id: str
    cafe_id: int | None = None
    start_time: datetime
    end_time: datetime | None = None
    duration_min: float | None = None
    gps_log_count: int = 0
    status: str

    model_config = {"from_attributes": True}
