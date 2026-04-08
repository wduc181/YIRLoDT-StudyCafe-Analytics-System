"""
session.py — Pydantic Schemas cho Session domain.

TODO:
- SessionStartRequest: device_id (required), cafe_id (optional).
- SessionStartResponse: status, session_id, started_at.
- SessionEndRequest: session_id (required).
- SessionEndResponse: status, session_id, ended_at, duration_min.
- SessionResponse: chi tiết session (session_id, device_id, cafe_id,
  start_time, end_time, duration_min, gps_log_count, status).
- Ref: docs/api_design.md mục 5.1, 5.3, 5.5.
"""
