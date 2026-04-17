"""
tracking.py — Pydantic Schemas cho GPS Tracking domain.
"""

from datetime import datetime

from pydantic import BaseModel, field_validator


class TrackingRequest(BaseModel):
    """Request body cho POST /api/tracking."""
    device_id: str
    session_id: str
    lat: float
    lng: float
    accuracy: float | None = None
    timestamp: datetime

    @field_validator("lat")
    @classmethod
    def validate_lat(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError("lat must be between -90 and 90")
        return v

    @field_validator("lng")
    @classmethod
    def validate_lng(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError("lng must be between -180 and 180")
        return v


class TrackingResponse(BaseModel):
    """Response cho POST /api/tracking."""
    status: str = "ok"
    log_id: int
