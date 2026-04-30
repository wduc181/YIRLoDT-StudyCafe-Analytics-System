# app/models/session_result.py
#
# Mapping bảng `session_results` — lưu kết quả scoring engine cho từng session.
#
# [AI-4 FIX] Tách biệt "session lifecycle" (bảng sessions) khỏi "scoring output"
# để nhất quán với pattern cafe_scores/cafes đã có.
#
# Lý do tạo bảng riêng thay vì thêm column vào sessions:
#   - sessions là lifecycle tracker (start/end/status); scoring chạy async
#     sau khi session end → không để cột NULL lởn vởn trong bảng lifecycle.
#   - Cho phép re-score với engine version khác mà không mất kết quả cũ.
#   - Nhất quán với cặp cafes ↔ cafe_scores đã thiết kế.

from sqlalchemy import (
    Column, BigInteger, Float, Boolean, Integer, String, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP

from app.db.database import Base


class SessionResult(Base):
    """Kết quả scoring engine cho một session."""

    __tablename__ = "session_results"

    # ── Identity ─────────────────────────────────────────────────────────────
    result_id  = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.session_id"),
        nullable=False,
        index=True,
    )
    cafe_id    = Column(Integer, ForeignKey("cafes.cafe_id"), nullable=True)
    computed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # ── Noise Filter ─────────────────────────────────────────────────────────
    total_gps_points  = Column(Integer,  nullable=True)
    clean_gps_points  = Column(Integer,  nullable=True)
    noise_point_count = Column(Integer,  nullable=True)
    clean_data_rate   = Column(Float,    nullable=True)

    # ── Study Detection ───────────────────────────────────────────────────────
    is_studying              = Column(Boolean, nullable=True)
    stable_duration_min      = Column(Float,   nullable=True)
    # session_duration_min: tổng thời gian session (GPS đầu → GPS cuối)
    # Đây là field quan trọng nhất cho batch mode — _get_duration() cần field này.
    session_duration_min     = Column(Float,   nullable=True)
    dominant_cluster_pct     = Column(Float,   nullable=True)
    spatial_std_m            = Column(Float,   nullable=True)
    coverage_ratio           = Column(Float,   nullable=True)
    cluster_count            = Column(Integer, nullable=True)
    centroid_distance_to_cafe_m = Column(Float, nullable=True)
    is_within_cafe_radius    = Column(Boolean, nullable=True)
    reason                   = Column(String(64), nullable=True)

    # ── Scoring ───────────────────────────────────────────────────────────────
    # session_score: weighted sum f2–f7 (không có f1 vì f1 là metric đa session)
    session_score = Column(Float, nullable=True)

    # ── Meta ──────────────────────────────────────────────────────────────────
    engine_version = Column(String(16), nullable=True)

    __table_args__ = (
        # Tối ưu truy vấn batch: lấy tất cả session results của 1 quán
        Index("idx_sr_cafe_id",     "cafe_id"),
        # Tối ưu lookup theo session
        Index("idx_sr_session_id",  "session_id"),
        # Tối ưu lọc theo is_studying (batch recalculation chỉ cần studying sessions)
        Index("idx_sr_is_studying", "is_studying"),
    )
