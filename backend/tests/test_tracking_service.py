"""
test_tracking_service.py — Unit tests cho tracking_service.
"""

import asyncio
import uuid
from datetime import datetime, timezone

from app.models.cafe import Cafe
from app.models.session import Session
from app.schemas.tracking import TrackingRequest
from app.services import tracking_service


class _FakeInsert:
    def values(self, **_kwargs):
        return self

    def on_conflict_do_nothing(self, **_kwargs):
        return self

    def returning(self, *_args):
        return self


class _FakeResult:
    def __init__(self, *, row=None, scalar=None):
        self._row = row
        self._scalar = scalar

    def fetchone(self):
        return self._row

    def scalar_one_or_none(self):
        return self._scalar


class _FakeDb:
    def __init__(self, results):
        self._results = list(results)
        self.commit_count = 0

    async def execute(self, _stmt):
        return self._results.pop(0)

    async def commit(self):
        self.commit_count += 1


def _session(session_id, cafe_id=None):
    return Session(
        session_id=session_id,
        device_id="device-001",
        cafe_id=cafe_id,
        start_time=datetime.now(timezone.utc),
        status="active",
    )


def _cafe(cafe_id=1, name="Cafe A"):
    return Cafe(
        cafe_id=cafe_id,
        name=name,
        address=f"{name} address",
        center_lat=21.0,
        center_lng=105.0,
        radius_meters=50,
        status="active",
    )


def _tracking_request(session_id):
    return TrackingRequest(
        device_id="device-001",
        session_id=str(session_id),
        lat=21.0,
        lng=105.0,
        accuracy=10.0,
        timestamp=datetime.now(timezone.utc),
    )


def test_record_gps_returns_existing_session_cafe(monkeypatch) -> None:
    monkeypatch.setattr(tracking_service, "pg_insert", lambda _model: _FakeInsert())

    session_id = uuid.uuid4()
    cafe = _cafe()
    db = _FakeDb(
        [
            _FakeResult(scalar=_session(session_id, cafe_id=cafe.cafe_id)),
            _FakeResult(row=(123,)),
            _FakeResult(scalar=cafe),
        ]
    )

    result = asyncio.run(tracking_service.record_gps(db, _tracking_request(session_id)))

    assert result.log_id == 123
    assert result.current_cafe.cafe_id == cafe.cafe_id
    assert result.current_cafe.name == cafe.name
    assert result.scoring_eligible is True


def test_record_gps_returns_resolved_cafe(monkeypatch) -> None:
    monkeypatch.setattr(tracking_service, "pg_insert", lambda _model: _FakeInsert())

    cafe = _cafe()

    async def fake_resolve_nearest_cafe(_db, _lat, _lng):
        return cafe

    monkeypatch.setattr(
        tracking_service, "resolve_nearest_cafe", fake_resolve_nearest_cafe
    )

    session_id = uuid.uuid4()
    session = _session(session_id)
    db = _FakeDb(
        [
            _FakeResult(scalar=session),
            _FakeResult(row=(123,)),
        ]
    )

    result = asyncio.run(tracking_service.record_gps(db, _tracking_request(session_id)))

    assert session.cafe_id == cafe.cafe_id
    assert result.current_cafe.name == cafe.name
    assert result.scoring_eligible is True
    assert db.commit_count == 2


def test_record_gps_returns_not_scoring_eligible_without_cafe(monkeypatch) -> None:
    monkeypatch.setattr(tracking_service, "pg_insert", lambda _model: _FakeInsert())

    async def fake_resolve_nearest_cafe(_db, _lat, _lng):
        return None

    monkeypatch.setattr(
        tracking_service, "resolve_nearest_cafe", fake_resolve_nearest_cafe
    )

    session_id = uuid.uuid4()
    db = _FakeDb(
        [
            _FakeResult(scalar=_session(session_id)),
            _FakeResult(row=(123,)),
        ]
    )

    result = asyncio.run(tracking_service.record_gps(db, _tracking_request(session_id)))

    assert result.current_cafe is None
    assert result.scoring_eligible is False
