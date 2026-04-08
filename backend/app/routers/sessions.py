"""
sessions.py — FastAPI Router: Session endpoints.

TODO:
- POST /api/session/start       → Tạo session mới.
                                   Gọi session_service.start_session().
- POST /api/session/end         → Kết thúc session + trigger scoring.
                                   Gọi session_service.end_session().
- GET  /api/session/{session_id} → Xem chi tiết session.
                                   Gọi session_service.get_session().
- Error format: {"status": "error", "message": "..."}.
- Ref: docs/api_design.md mục 5.1, 5.3, 5.5.
"""
