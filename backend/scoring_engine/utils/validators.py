"""
utils/validators.py — Validate và normalize input payload trước khi xử lý.

Bắt lỗi sớm, raise ValueError với message rõ ràng để pipeline không crash âm thầm.
"""

from datetime import datetime, timezone
from typing import Any

from dateutil import parser as dateutil_parser

from scoring_engine import config

# ============================================================
# Validate toàn bộ payload đầu vào
# ============================================================

def validate_payload(payload: dict) -> None:
    """
    Kiểm tra payload đầu vào có đủ fields bắt buộc và hợp lệ.

    Raises:
        ValueError: nếu payload thiếu field hoặc giá trị không hợp lệ.
    """
    _require_fields(payload, ["session_id", "device_id", "cafe", "gps_points"])

    # Validate cafe
    cafe = payload["cafe"]
    _require_fields(cafe, ["cafe_id", "center_lat", "center_lng", "radius_meters"],
                    context="cafe")
    _validate_coords(cafe["center_lat"], cafe["center_lng"], context="cafe center")

    # Validate gps_points
    gps_points = payload["gps_points"]
    if not isinstance(gps_points, list):
        raise ValueError("gps_points phải là list")

    # Validate từng điểm GPS
    for idx, pt in enumerate(gps_points):
        _validate_gps_point(pt, idx)


def validate_and_parse_gps_points(gps_points: list[dict]) -> list[dict]:
    """
    Parse timestamp từ string ISO 8601 → datetime object (có timezone).
    Sort theo timestamp tăng dần.

    Returns:
        List điểm GPS đã được parse và sort.

    Raises:
        ValueError: nếu timestamp có format sai.
    """
    parsed = []
    for idx, pt in enumerate(gps_points):
        pt_copy = dict(pt)
        ts = pt_copy.get("timestamp")
        if isinstance(ts, str):
            try:
                dt = dateutil_parser.isoparse(ts)
                # Đảm bảo có timezone info
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                pt_copy["timestamp"] = dt
            except (ValueError, OverflowError) as e:
                raise ValueError(
                    f"Điểm GPS [{idx}]: timestamp '{ts}' không đúng format ISO 8601. "
                    f"Chi tiết: {e}"
                )
        elif not isinstance(ts, datetime):
            raise ValueError(
                f"Điểm GPS [{idx}]: timestamp phải là string ISO 8601 hoặc datetime object, "
                f"nhận được {type(ts).__name__}"
            )
        parsed.append(pt_copy)

    # Sort theo timestamp tăng dần (đề phòng frontend gửi không theo thứ tự)
    parsed.sort(key=lambda p: p["timestamp"])
    return parsed


# ============================================================
# Validate cafe_history (optional field)
# ============================================================

def normalize_cafe_history(cafe_history: Any) -> dict | None:
    """
    Normalize cafe_history — trả về None nếu không có hoặc không hợp lệ.
    Không raise lỗi vì cafe_history là optional.
    """
    if cafe_history is None:
        return None
    if not isinstance(cafe_history, dict):
        return None

    return {
        "total_sessions_processed": int(cafe_history.get("total_sessions_processed", 0)),
        "current_score":            cafe_history.get("current_score"),           # có thể None
        "studying_session_count":   int(cafe_history.get("studying_session_count", 0)),
        "system_avg_score": float(cafe_history.get("system_avg_score", config.DEFAULT_SYSTEM_AVG)),
    }


# ============================================================
# Helpers
# ============================================================

def _require_fields(obj: dict, fields: list[str], context: str = "payload") -> None:
    for field in fields:
        if field not in obj or obj[field] is None:
            raise ValueError(f"{context}: field '{field}' bắt buộc nhưng bị thiếu hoặc null")


def _validate_coords(lat: float, lng: float, context: str = "") -> None:
    if not (-90 <= lat <= 90):
        raise ValueError(f"{context}: latitude {lat} nằm ngoài phạm vi [-90, 90]")
    if not (-180 <= lng <= 180):
        raise ValueError(f"{context}: longitude {lng} nằm ngoài phạm vi [-180, 180]")


def _validate_gps_point(pt: dict, idx: int) -> None:
    _require_fields(pt, ["lat", "lng", "timestamp"], context=f"gps_points[{idx}]")
    try:
        lat = float(pt["lat"])
        lng = float(pt["lng"])
    except (TypeError, ValueError):
        raise ValueError(f"gps_points[{idx}]: lat/lng phải là số")
    _validate_coords(lat, lng, context=f"gps_points[{idx}]")
