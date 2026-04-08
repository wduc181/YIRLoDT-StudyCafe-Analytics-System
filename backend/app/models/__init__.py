"""
models/__init__.py — ORM Models package init.

Import tất cả models ở đây để Alembic detect và Base.metadata chứa đủ tables.
"""

from app.models.cafe import Cafe
from app.models.session import Session
from app.models.gps_log import GpsLog
from app.models.cafe_score import CafeScore

__all__ = ["Cafe", "Session", "GpsLog", "CafeScore"]
