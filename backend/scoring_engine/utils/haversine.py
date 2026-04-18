"""
utils/haversine.py — Tính khoảng cách GPS bằng công thức Haversine.

Hàm duy nhất để tính khoảng cách GPS trong toàn bộ scoring engine.
Tương thích với backend/app/internal/haversine.py (khi team Dev implement).
"""

import math


EARTH_RADIUS_M = 6_371_000.0  # bán kính Trái Đất (mét)


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Tính khoảng cách (mét) giữa hai điểm GPS theo công thức Haversine.

    Args:
        lat1, lng1: Tọa độ điểm 1 (độ thập phân).
        lat2, lng2: Tọa độ điểm 2 (độ thập phân).

    Returns:
        Khoảng cách tính bằng mét (float).
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lng2 - lng1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_M * c


def haversine_from_dicts(p1: dict, p2: dict) -> float:
    """
    Tiện ích: nhận dict {"lat": ..., "lng": ...} thay vì 4 tham số riêng.

    Args:
        p1, p2: dict với keys "lat" và "lng".

    Returns:
        Khoảng cách tính bằng mét.
    """
    return haversine_m(p1["lat"], p1["lng"], p2["lat"], p2["lng"])
