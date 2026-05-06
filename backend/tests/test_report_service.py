"""
test_report_service.py — Tests for Excel report export.

Run: pytest backend/tests/test_report_service.py -v
"""

import asyncio
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from openpyxl import load_workbook

from app.services import report_service


def _scalars_result(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _rows_result(rows):
    result = MagicMock()
    result.all.return_value = rows
    return result


def test_generate_report_falls_back_to_session_results_for_avg_stable_duration(
    monkeypatch,
):
    """
    CafeScore incremental rows may have avg_stable_duration_min=None.
    Excel should still show the average from persisted studying session_results.
    """
    cafe = SimpleNamespace(cafe_id=1, name="Cafe A")
    score = SimpleNamespace(
        total_sessions=3,
        studying_sessions=2,
        study_rate=0.6667,
        avg_stable_duration_min=None,
        dropoff_rate=0.3333,
        behavior_score=7.1,
        has_enough_data=False,
    )

    db = AsyncMock()
    db.execute.side_effect = [
        _scalars_result([cafe]),
        _rows_result([(1, 72.75)]),
    ]

    async def fake_get_latest_scores_by_cafe_id(_db, cafe_ids):
        assert cafe_ids == [1]
        return {1: score}

    monkeypatch.setattr(
        report_service,
        "get_latest_scores_by_cafe_id",
        fake_get_latest_scores_by_cafe_id,
    )

    output = asyncio.run(report_service.generate_report(db))
    wb = load_workbook(io.BytesIO(output.getvalue()))
    ws = wb["StudyCafe Report"]

    assert ws.cell(row=2, column=6).value == 72.8


def test_generate_report_keeps_cafe_score_avg_when_present(monkeypatch):
    """CafeScore aggregate value remains the source of truth when available."""
    cafe = SimpleNamespace(cafe_id=1, name="Cafe A")
    score = SimpleNamespace(
        total_sessions=3,
        studying_sessions=2,
        study_rate=0.6667,
        avg_stable_duration_min=65.0,
        dropoff_rate=0.3333,
        behavior_score=7.1,
        has_enough_data=False,
    )

    db = AsyncMock()
    db.execute.side_effect = [
        _scalars_result([cafe]),
        _rows_result([(1, 72.75)]),
    ]

    async def fake_get_latest_scores_by_cafe_id(_db, cafe_ids):
        assert cafe_ids == [1]
        return {1: score}

    monkeypatch.setattr(
        report_service,
        "get_latest_scores_by_cafe_id",
        fake_get_latest_scores_by_cafe_id,
    )

    output = asyncio.run(report_service.generate_report(db))
    wb = load_workbook(io.BytesIO(output.getvalue()))
    ws = wb["StudyCafe Report"]

    assert ws.cell(row=2, column=6).value == 65.0
