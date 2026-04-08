"""
gps_log.py — SQLAlchemy ORM Model: GpsLog.

TODO:
- Tạo class GpsLog(Base) mapping bảng `gps_logs`.
- Columns: log_id (BIGSERIAL PK), session_id (FK → sessions),
  device_id, lat, lng, accuracy_m, timestamp, is_noise (default False).
- UNIQUE constraint: (session_id, timestamp) → chống duplicate.
- Indexes: idx_gps_session_time, idx_gps_device_time, idx_gps_timestamp.
- Ref: docs/api_design.md mục 8.3.
"""
