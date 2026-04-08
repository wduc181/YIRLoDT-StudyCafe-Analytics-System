"""
cafe.py — Pydantic Schemas cho Cafe domain.

TODO:
- CafeCreate: schema cho POST /api/cafes/suggest (name, address, center_lat,
  center_lng, google_place_id, device_id).
- CafeResponse: schema trả về từ GET /api/cafes (cafe_id, name, address,
  center_lat, center_lng, radius_meters, behavior_score, has_enough_data).
- CafeNearbyResponse: kế thừa CafeResponse + distance_meters, google_maps_url.
- Ref: docs/api_design.md mục 5.4, 5.8, 5.9.
"""
