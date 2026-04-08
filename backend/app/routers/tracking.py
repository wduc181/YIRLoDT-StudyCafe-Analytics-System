"""
tracking.py — FastAPI Router: GPS Tracking endpoint.

TODO:
- POST /api/tracking → Nhận GPS log từ frontend trong lúc session đang chạy.
                        Gọi tracking_service.record_gps().
- Validate session_id tồn tại.
- Chống duplicate bằng ON CONFLICT (session_id, timestamp) DO NOTHING.
- Nếu GPS đầu tiên + session chưa có cafe_id → resolve quán gần nhất.
- Ref: docs/api_design.md mục 5.2.
"""
