"""
report.py — Pydantic Schemas cho Report/Export domain.

Ref: docs/api_design.md mục 5.6.
"""

from pydantic import BaseModel


class ReportRow(BaseModel):
    """Schema cho mỗi row trong Excel export."""
    cafe_id: int
    name: str
    total_visits: int | None = None
    avg_duration: float | None = None
    dropoff_rate: float | None = None
    behavior_score: float | None = None
    has_enough_data: bool = False

    model_config = {"from_attributes": True}
