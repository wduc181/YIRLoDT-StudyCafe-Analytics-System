"""
report.py — Pydantic Schemas cho Report/Export domain.
"""

from pydantic import BaseModel


class ReportRow(BaseModel):
    """Schema cho mỗi row trong Excel export — khớp CafeScore Bayesian."""
    cafe_id: int
    name: str
    total_sessions: int | None = None
    studying_sessions: int | None = None
    study_rate: float | None = None
    avg_stable_duration_min: float | None = None
    dropoff_rate: float | None = None
    behavior_score: float | None = None
    has_enough_data: bool = False

    model_config = {"from_attributes": True}
