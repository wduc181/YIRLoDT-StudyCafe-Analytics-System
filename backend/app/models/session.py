"""
session.py — SQLAlchemy ORM Model: Session.

TODO:
- Tạo class Session(Base) mapping bảng `sessions`.
- Columns: session_id (UUID PK), device_id, cafe_id (FK → cafes),
  start_time, end_time (nullable), duration_min (nullable),
  status (default 'active').
- Ref: docs/api_design.md mục 8.2.
"""
