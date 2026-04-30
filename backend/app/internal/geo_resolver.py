"""
geo_resolver.py — Resolve quán cafe gần nhất từ tọa độ GPS.

TODO:
- resolve_nearest_cafe(db, lat, lng) → Cafe | None.
  Tính Haversine distance đến tất cả quán active, trả về quán
  gần nhất nằm trong radius_meters. Trả None nếu không có quán nào.
- Dùng internal/haversine.py để tính khoảng cách.
- Được gọi từ tracking_service khi GPS đầu tiên và session chưa có cafe_id.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.internal.haversine import haversine_distance
from app.models.cafe import Cafe


async def resolve_nearest_cafe(db: AsyncSession, lat: float, lng: float) -> Cafe | None:
  """Trả về quán active gần nhất nằm trong radius_meters."""
  stmt = select(Cafe).where(Cafe.status == "active")
  result = await db.execute(stmt)
  cafes = result.scalars().all()

  nearest_cafe = None
  nearest_distance = None

  for cafe in cafes:
    distance = haversine_distance(lat, lng, cafe.center_lat, cafe.center_lng)
    if distance > (cafe.radius_meters or 0):
      continue

    if nearest_distance is None or distance < nearest_distance:
      nearest_cafe = cafe
      nearest_distance = distance

  return nearest_cafe
