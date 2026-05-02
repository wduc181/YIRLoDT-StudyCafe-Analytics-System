"""
test_cafe_score_service.py — Tests for get_latest_scores_by_cafe_id.

File này có unit tests dùng mock DB cho edge cases cơ bản và một SQLite-backed
query test để thực thi SQLAlchemy window function + aliased subquery thật.

Run: pytest backend/tests/test_cafe_score_service.py -v
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SyncSession

from app.models.cafe import Cafe
from app.models.cafe_score import CafeScore
from app.services.cafe_score_service import get_latest_scores_by_cafe_id


class _AsyncDbWrapper:
    def __init__(self, session):
        self.session = session

    async def execute(self, stmt):
        return self.session.execute(stmt)


def test_empty_cafe_ids_returns_empty_dict():
    """cafe_ids=[] → trả {} ngay, không query DB."""
    db = AsyncMock()
    result = asyncio.run(get_latest_scores_by_cafe_id(db, []))
    assert result == {}
    db.execute.assert_not_called()


def test_returns_latest_score_per_cafe():
    """
    Giả lập DB trả 2 scores cho 2 cafes khác nhau,
    assert helper trả đúng mapping cafe_id → CafeScore.
    """
    # Tạo mock CafeScore objects
    score_cafe_1 = MagicMock(spec=CafeScore)
    score_cafe_1.cafe_id = 1
    score_cafe_1.behavior_score = 8.5
    score_cafe_1.computed_at = datetime(2026, 5, 1, tzinfo=timezone.utc)

    score_cafe_2 = MagicMock(spec=CafeScore)
    score_cafe_2.cafe_id = 2
    score_cafe_2.behavior_score = 7.0
    score_cafe_2.computed_at = datetime(2026, 5, 1, tzinfo=timezone.utc)

    # Mock db.execute → result.scalars().all()
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [score_cafe_1, score_cafe_2]
    db.execute.return_value = mock_result

    result = asyncio.run(get_latest_scores_by_cafe_id(db, [1, 2]))

    assert len(result) == 2
    assert result[1].cafe_id == 1
    assert result[1].behavior_score == 8.5
    assert result[2].cafe_id == 2


def test_cafe_without_score_not_in_result():
    """
    Nếu cafe_id=3 không có CafeScore nào → không có trong dict.
    """
    score_cafe_1 = MagicMock(spec=CafeScore)
    score_cafe_1.cafe_id = 1
    score_cafe_1.behavior_score = 6.0

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [score_cafe_1]
    db.execute.return_value = mock_result

    result = asyncio.run(get_latest_scores_by_cafe_id(db, [1, 3]))

    assert 1 in result
    assert 3 not in result


def test_query_returns_latest_score_per_cafe_with_tie_breaker():
    """
    Execute the real SQLAlchemy query against SQLite.

    Cafe 1: latest by computed_at.
    Cafe 2: same computed_at, latest by higher score_id.
    Cafe 3: no score, absent from result.
    """
    engine = create_engine("sqlite:///:memory:")
    Cafe.__table__.create(engine)
    CafeScore.__table__.create(engine)

    computed_at = datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc)
    with SyncSession(engine) as session:
        session.add_all(
            [
                Cafe(
                    cafe_id=1,
                    name="Cafe A",
                    center_lat=21.0,
                    center_lng=105.0,
                    status="active",
                ),
                Cafe(
                    cafe_id=2,
                    name="Cafe B",
                    center_lat=21.1,
                    center_lng=105.1,
                    status="active",
                ),
                Cafe(
                    cafe_id=3,
                    name="Cafe C",
                    center_lat=21.2,
                    center_lng=105.2,
                    status="active",
                ),
            ]
        )
        session.add_all(
            [
                CafeScore(
                    cafe_id=1,
                    computed_at=computed_at - timedelta(days=1),
                    behavior_score=5.0,
                    has_enough_data=True,
                ),
                CafeScore(
                    cafe_id=1,
                    computed_at=computed_at,
                    behavior_score=8.0,
                    has_enough_data=True,
                ),
                CafeScore(
                    cafe_id=2,
                    computed_at=computed_at,
                    behavior_score=6.0,
                    has_enough_data=True,
                ),
                CafeScore(
                    cafe_id=2,
                    computed_at=computed_at,
                    behavior_score=7.0,
                    has_enough_data=True,
                ),
            ]
        )
        session.commit()

        result = asyncio.run(
            get_latest_scores_by_cafe_id(_AsyncDbWrapper(session), [1, 2, 3])
        )

        assert set(result) == {1, 2}
        assert result[1].behavior_score == 8.0
        assert result[2].behavior_score == 7.0
