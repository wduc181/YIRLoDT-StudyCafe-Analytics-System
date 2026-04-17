"""Unit tests cho session/session schema behavior."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.session import SessionEndRequest


def test_session_end_request_accepts_valid_uuid() -> None:
	session_id = str(uuid4())
	payload = SessionEndRequest(session_id=session_id)

	assert str(payload.session_id) == session_id


def test_session_end_request_rejects_invalid_uuid() -> None:
	with pytest.raises(ValidationError):
		SessionEndRequest(session_id="invalid-uuid")
