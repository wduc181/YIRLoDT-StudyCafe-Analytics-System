"""
scoring_service.py — Interface gọi Scoring Engine.

TODO:
- score_session(db, session_id) → Chuẩn bị input data theo contract
  (docs/api_design.md mục 6.1), gọi scoring engine, nhận output
  (mục 6.2), lưu kết quả vào bảng cafe_scores.
- QUAN TRỌNG: Không tự implement logic scoring ở đây.
  Scoring engine do team riêng phụ trách (xem scoring_engine_design.md).
  File này chỉ là interface/adapter layer.
- Chờ Scoring team chốt: real-time hay batch? function call hay DB?
- Ref: AGENTS.md mục 10, docs/api_design.md mục 6.
"""
