"""
cafe_score.py — SQLAlchemy ORM Model: CafeScore.

TODO:
- Tạo class CafeScore(Base) mapping bảng `cafe_scores`.
- Columns: score_id (PK), cafe_id (FK → cafes), computed_at (default NOW),
  total_visits, avg_duration, dropoff_rate, behavior_score,
  has_enough_data (default False).
- Ref: docs/api_design.md mục 8.4.
"""
