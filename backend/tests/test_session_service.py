"""Unit tests cho session/session service behavior."""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.session import Session
from app.schemas.session import SessionEndRequest
from app.services import session_service


class _FakeResult:
	def __init__(self, scalar=None):
		self._scalar = scalar

	def scalar_one_or_none(self):
		return self._scalar


class _FakeDb:
	def __init__(self, session):
		self._session = session
		self.commit_count = 0

	async def execute(self, _stmt):
		return _FakeResult(scalar=self._session)

	async def commit(self):
		self.commit_count += 1


class _FakeBackgroundTasks:
	def __init__(self):
		self.tasks = []

	def add_task(self, func, *args, **kwargs):
		self.tasks.append((func, args, kwargs))


def _session(status="active"):
	return Session(
		session_id=uuid4(),
		device_id="device-001",
		cafe_id=1,
		start_time=datetime.now(timezone.utc) - timedelta(minutes=30),
		status=status,
	)


def test_session_end_request_accepts_valid_uuid() -> None:
	session_id = str(uuid4())
	payload = SessionEndRequest(session_id=session_id)

	assert str(payload.session_id) == session_id


def test_session_end_request_rejects_invalid_uuid() -> None:
	with pytest.raises(ValidationError):
		SessionEndRequest(session_id="invalid-uuid")


def test_end_session_returns_existing_completed_session_and_retriggers_scoring() -> None:
	session = _session(status="completed")
	session.end_time = datetime.now(timezone.utc)
	session.duration_min = 30.0
	db = _FakeDb(session)
	background_tasks = _FakeBackgroundTasks()
	request = SessionEndRequest(session_id=session.session_id)

	result = asyncio.run(session_service.end_session(db, request, background_tasks))

	assert result.status == "ok"
	assert result.session_id == str(session.session_id)
	assert result.ended_at == session.end_time
	assert result.duration_min == session.duration_min
	assert db.commit_count == 0
	assert len(background_tasks.tasks) == 1
	assert background_tasks.tasks[0][0] is session_service._run_scoring_background
	assert background_tasks.tasks[0][1] == (str(session.session_id),)


def test_end_session_marks_active_session_completed_and_triggers_scoring() -> None:
	session = _session(status="active")
	db = _FakeDb(session)
	background_tasks = _FakeBackgroundTasks()
	request = SessionEndRequest(session_id=session.session_id)

	result = asyncio.run(session_service.end_session(db, request, background_tasks))

	assert result.status == "ok"
	assert result.session_id == str(session.session_id)
	assert session.status == "completed"
	assert session.end_time is not None
	assert session.duration_min is not None
	assert db.commit_count == 1
	assert len(background_tasks.tasks) == 1
	assert background_tasks.tasks[0][0] is session_service._run_scoring_background
	assert background_tasks.tasks[0][1] == (str(session.session_id),)
