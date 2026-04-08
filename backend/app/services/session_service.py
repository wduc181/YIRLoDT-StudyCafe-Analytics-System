"""
session_service.py — Business Logic: Session operations.

TODO:
- start_session(db, data) → Tạo session mới với UUID, status='active'.
  device_id bắt buộc, cafe_id optional (resolve sau từ GPS đầu tiên).
- end_session(db, session_id) → Cập nhật end_time, tính duration_min,
  status='completed'. Có thể trigger scoring_service sau khi kết thúc.
- get_session(db, session_id) → Lấy chi tiết session + gps_log_count.
- Mọi DB operation dùng async/await.
- Ref: docs/api_design.md mục 5.1, 5.3, 5.5.
"""
