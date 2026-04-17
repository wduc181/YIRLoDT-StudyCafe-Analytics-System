# Mapping bảng `gps_logs` — lưu điểm GPS theo session.
# UNIQUE constraint: (session_id, timestamp) → chống duplicate.

from sqlalchemy import Column, BigInteger, Float, Boolean, String, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP

from app.db.database import Base


class GpsLog(Base):
    """Một điểm dữ liệu vị trí GPS trong session."""

    __tablename__ = "gps_logs"

    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id"), nullable=False)
    device_id = Column(String(64), nullable=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    accuracy_m = Column(Float, nullable=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    is_noise = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("session_id", "timestamp", name="uq_gps_session_timestamp"),
        Index("idx_gps_session_time", "session_id", "timestamp"),
        Index("idx_gps_device_time", "device_id", "timestamp"),
        Index("idx_gps_timestamp", "timestamp"),
    )
