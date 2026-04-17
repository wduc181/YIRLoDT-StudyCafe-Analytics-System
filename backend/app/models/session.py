# Mapping bảng `sessions` — lưu phiên học tập của người dùng.

import uuid

from sqlalchemy import Column, String, Float, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP

from app.db.database import Base


class Session(Base):
    """Một phiên học tập của người dùng."""

    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(64), nullable=False)
    cafe_id = Column(Integer, ForeignKey("cafes.cafe_id"), nullable=True)
    start_time = Column(TIMESTAMP(timezone=True), nullable=False)
    end_time = Column(TIMESTAMP(timezone=True), nullable=True)
    duration_min = Column(Float, nullable=True)
    status = Column(String(32), default="active")
