"""
cafes.py — FastAPI Router: Cafe endpoints.

TODO:
- GET  /api/cafes          → Lấy danh sách quán cafe + điểm đánh giá.
                              Gọi cafe_service.get_all_cafes().
- GET  /api/cafes/nearby   → [Optional] Lấy quán gần nhất theo GPS.
                              Query params: lat, lng, radius, limit.
                              Gọi cafe_service.get_nearby_cafes().
- POST /api/cafes/suggest  → [Optional] Đề xuất thêm quán mới.
                              Gọi cafe_service.suggest_cafe().
- Mọi endpoint dùng Pydantic schema, không trả dict raw.
- Ref: docs/api_design.md mục 5.4, 5.8, 5.9.
"""
