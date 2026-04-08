"""
tracking.py — Pydantic Schemas cho GPS Tracking domain.

TODO:
- TrackingRequest: device_id, session_id, lat, lng, accuracy, timestamp.
- TrackingResponse: status, log_id.
- Validate lat trong [-90, 90], lng trong [-180, 180].
- Ref: docs/api_design.md mục 5.2.
"""
