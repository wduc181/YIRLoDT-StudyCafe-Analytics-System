"""
haversine.py — Tính khoảng cách GPS bằng công thức Haversine.

TODO:
- haversine_distance(lat1, lng1, lat2, lng2) → float (meters).
- Đây là hàm duy nhất để tính khoảng cách GPS trong toàn hệ thống.
- AGENTS.md rule 9.2: "Tính khoảng cách GPS dùng internal/haversine.py,
  không tự viết công thức."
"""

from math import asin, cos, radians, sin, sqrt


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Tính khoảng cách giữa hai tọa độ GPS theo mét."""
    earth_radius_m = 6_371_000

    delta_lat = radians(lat2 - lat1)
    delta_lng = radians(lng2 - lng1)
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng / 2) ** 2
    )
    c = 2 * asin(sqrt(a))
    return earth_radius_m * c
