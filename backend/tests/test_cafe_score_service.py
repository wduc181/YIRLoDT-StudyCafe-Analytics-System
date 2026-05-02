"""
test_cafe_score_service.py — Integration Tests: get_latest_scores_by_cafe_id.

Tests cần DB thật (hoặc test DB) vì query dùng window function + aliased subquery
mà unit test với mock db.execute không cover được runtime mapping.

Run: pytest backend/tests/test_cafe_score_service.py -v
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.cafe_score import CafeScore
from app.services.cafe_score_service import get_latest_scores_by_cafe_id


# ── Unit tests cho edge cases cơ bản ──────────────────────


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
