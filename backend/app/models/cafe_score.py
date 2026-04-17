# Mapping bảng `cafe_scores` — kết quả đánh giá hành vi theo quán.

from sqlalchemy import Column, Integer, Float, Boolean, String, ForeignKey, func
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.db.database import Base


class CafeScore(Base):
    """Kết quả đánh giá hành vi của một quán cafe (Bayesian scoring)."""

    __tablename__ = "cafe_scores"

    score_id = Column(Integer, primary_key=True, autoincrement=True)
    cafe_id = Column(Integer, ForeignKey("cafes.cafe_id"), nullable=False)
    computed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Aggregate stats
    total_sessions = Column(Integer, nullable=True)
    studying_sessions = Column(Integer, nullable=True)
    study_rate = Column(Float, nullable=True)
    avg_stable_duration_min = Column(Float, nullable=True)
    avg_spatial_std_m = Column(Float, nullable=True)
    dropoff_count = Column(Integer, nullable=True)
    dropoff_rate = Column(Float, nullable=True)

    # Bayesian Score
    behavior_score = Column(Float, nullable=True)
    has_enough_data = Column(Boolean, default=False)
    bayesian_m = Column(Integer, nullable=True)
    prior_score = Column(Float, nullable=True)

    # Meta
    engine_version = Column(String(16), nullable=True)
