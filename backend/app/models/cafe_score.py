"""
cafe_score.py — SQLAlchemy ORM Model: CafeScore.

Mapping bảng `cafe_scores` — kết quả đánh giá hành vi theo quán.
Ref: docs/api_design.md mục 8.4.
"""

from sqlalchemy import Column, Integer, Float, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.db.database import Base


class CafeScore(Base):
    """Kết quả đánh giá hành vi của một quán cafe."""

    __tablename__ = "cafe_scores"

    score_id = Column(Integer, primary_key=True, autoincrement=True)
    cafe_id = Column(Integer, ForeignKey("cafes.cafe_id"), nullable=False)
    computed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    total_visits = Column(Integer, nullable=True)
    avg_duration = Column(Float, nullable=True)
    dropoff_rate = Column(Float, nullable=True)
    behavior_score = Column(Float, nullable=True)
    has_enough_data = Column(Boolean, default=False)
