"""
cafe_service.py — Business Logic: Cafe operations.

TODO:
- get_all_cafes(db) → Lấy danh sách quán (status='active') kèm score mới nhất.
- get_nearby_cafes(db, lat, lng, radius, limit) → [Optional] Tính khoảng cách
  Haversine, sort, trả top N. Dùng internal/haversine.py.
- suggest_cafe(db, data) → [Optional] Tạo quán mới status='pending'.
- approve_cafe(db, cafe_id) → [Optional] Chuyển status sang 'active'.
- Mọi DB operation dùng async/await.
- Ref: AGENTS.md mục 9.2.
"""
