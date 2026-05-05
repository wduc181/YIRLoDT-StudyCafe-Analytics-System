"""
test_cafe_service.py — Unit tests cho cafe_service.
"""

import asyncio

from app.models.cafe import Cafe
from app.models.cafe_score import CafeScore
from app.services.cafe_service import get_all_cafes


class _FakeScalarResult:
    def __init__(self, cafes):
        self._cafes = cafes

    def all(self):
        return self._cafes


class _FakeCafeResult:
    def __init__(self, cafes):
        self._cafes = cafes

    def scalars(self):
        return _FakeScalarResult(self._cafes)


class _FakeScoreScalars:
    def __init__(self, scores):
        self._scores = scores

    def all(self):
        return self._scores


class _FakeScoreResult:
    def __init__(self, scores):
        self._scores = scores

    def scalars(self):
        return _FakeScoreScalars(self._scores)


class _FakeDb:
    def __init__(self, cafes, scores):
        self._cafes = cafes
        self._scores = list(scores)
        self._execute_count = 0

    async def execute(self, _stmt):
        self._execute_count += 1
        if self._execute_count == 1:
            return _FakeCafeResult(self._cafes)

        return _FakeScoreResult(self._scores)


def _cafe(cafe_id, name, lat, lng):
    return Cafe(
        cafe_id=cafe_id,
        name=name,
        address=f"{name} address",
        center_lat=lat,
        center_lng=lng,
        radius_meters=50,
        status="active",
    )


def _score(cafe_id, behavior_score=8.0):
    return CafeScore(
        cafe_id=cafe_id,
        behavior_score=behavior_score,
        has_enough_data=True,
    )


def test_get_all_cafes_returns_maps_url_without_gps() -> None:
    db = _FakeDb([_cafe(1, "Cafe A", 21.0, 105.0)], [_score(1)])

    result = asyncio.run(get_all_cafes(db))

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].distance_meters is None
    assert result.items[0].google_maps_url == "https://www.google.com/maps?q=21.0,105.0"


def test_get_all_cafes_filters_and_sorts_by_distance() -> None:
    cafes = [
        _cafe(1, "Far", 0.0, 2.0),
        _cafe(2, "Near", 0.0, 0.0),
        _cafe(3, "Middle", 0.0, 1.0),
    ]
    db = _FakeDb(cafes, [_score(1), _score(2), _score(3)])

    result = asyncio.run(
        get_all_cafes(db, lat=0.0, lng=0.0, radius=150_000, limit=20)
    )

    assert [cafe.cafe_id for cafe in result.items] == [2, 3]
    assert result.items[0].distance_meters == 0
    assert result.items[1].distance_meters > result.items[0].distance_meters


def test_get_all_cafes_supports_min_radius_bucket() -> None:
    cafes = [
        _cafe(1, "Within 5km", 0.0, 0.01),
        _cafe(2, "Between 5 and 15km", 0.0, 0.08),
        _cafe(3, "Over 15km", 0.0, 0.2),
    ]
    db = _FakeDb(cafes, [_score(1), _score(2), _score(3)])

    result = asyncio.run(
        get_all_cafes(
            db,
            lat=0.0,
            lng=0.0,
            radius=15_000,
            min_radius=5_000,
            limit=20,
        )
    )

    assert [cafe.cafe_id for cafe in result.items] == [2]


def test_get_all_cafes_paginates_after_sorting() -> None:
    cafes = [
        _cafe(1, "Far", 0.0, 2.0),
        _cafe(2, "Near", 0.0, 0.0),
        _cafe(3, "Middle", 0.0, 1.0),
    ]
    db = _FakeDb(cafes, [_score(1), _score(2), _score(3)])

    result = asyncio.run(
        get_all_cafes(db, lat=0.0, lng=0.0, page=2, limit=1)
    )

    assert result.total == 3
    assert result.total_pages == 3
    assert result.has_next is True
    assert result.has_previous is True
    assert [cafe.cafe_id for cafe in result.items] == [3]
