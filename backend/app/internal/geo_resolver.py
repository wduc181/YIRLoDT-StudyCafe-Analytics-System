"""
geo_resolver.py — Resolve quán cafe gần nhất từ tọa độ GPS.

TODO:
- resolve_nearest_cafe(db, lat, lng) → Cafe | None.
  Tính Haversine distance đến tất cả quán active, trả về quán
  gần nhất nằm trong radius_meters. Trả None nếu không có quán nào.
- Dùng internal/haversine.py để tính khoảng cách.
- Được gọi từ tracking_service khi GPS đầu tiên và session chưa có cafe_id.
"""
