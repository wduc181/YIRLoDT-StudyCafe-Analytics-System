"""
tracking_service.py — Business Logic: GPS Tracking.

TODO:
- record_gps(db, data) → Lưu GPS log vào DB.
  - Validate session_id tồn tại và đang active.
  - Dùng ON CONFLICT (session_id, timestamp) DO NOTHING để chống duplicate.
  - Nếu GPS đầu tiên + session chưa có cafe_id → gọi geo_resolver
    để resolve quán gần nhất và cập nhật session.
- Mọi DB operation dùng async/await.
- Ref: docs/api_design.md mục 5.2.
"""
