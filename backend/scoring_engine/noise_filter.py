"""
noise_filter.py — Bước 2: Lọc nhiễu GPS (3 lớp tuần tự).

Lớp A: Accuracy threshold  — lọc cứng theo field accuracy
Lớp B: Speed filter         — vi phạm vật lý (Haversine + time delta)
Lớp C: Hampel Identifier    — outlier thống kê dựa trên MAD sliding window

Điểm nhiễu KHÔNG bị xóa — chỉ đánh dấu is_noise=True để giữ audit trail.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np

from scoring_engine import config
from scoring_engine.utils.haversine import haversine_m


# ============================================================
# Public API
# ============================================================

def apply_noise_filter(
    gps_points: list[dict],
    cafe_center_lat: float,
    cafe_center_lng: float,
    cafe_radius_m: float,
) -> tuple[list[dict], dict]:
    """
    Áp dụng 3 lớp lọc nhiễu tuần tự lên danh sách GPS points đã được parse/sort.

    Args:
        gps_points: list dict với keys {lat, lng, accuracy (optional), timestamp (datetime)}.
                    Đã được sort theo timestamp tăng dần.
        cafe_center_lat, cafe_center_lng: tọa độ trung tâm quán.
        cafe_radius_m: bán kính quán (mét).

    Returns:
        (annotated_points, summary)
        - annotated_points: bản copy của gps_points, mỗi dict thêm keys:
            is_noise (bool), noise_reason (str | None)
        - summary: dict thống kê {total_points, noise_count, clean_count, clean_rate}
    """
    # Khởi tạo: clone và thêm trường noise
    points = [
        {**pt, "is_noise": False, "noise_reason": None}
        for pt in gps_points
    ]

    geofence_radius = cafe_radius_m * config.GEOFENCE_MULTIPLIER

    # Lớp A: Accuracy threshold
    _filter_accuracy(points)

    # Lớp B: Speed filter + duplicate timestamp
    _filter_speed(points)

    # Hard rule: Geofence — nằm ngoài 2× radius
    _filter_geofence(points, cafe_center_lat, cafe_center_lng, geofence_radius)

    # Lớp C: Hampel Identifier (chỉ trên điểm chưa bị đánh nhiễu)
    _filter_hampel(points)

    # Summary
    noise_count = sum(1 for p in points if p["is_noise"])
    clean_count = len(points) - noise_count
    summary = {
        "total_points": len(points),
        "noise_count": noise_count,
        "clean_count": clean_count,
        "clean_rate": round(clean_count / len(points), 4) if points else 0.0,
    }

    return points, summary


# ============================================================
# Lớp A: Accuracy threshold
# ============================================================

def _filter_accuracy(points: list[dict]) -> None:
    """Đánh dấu điểm có accuracy > ngưỡng là nhiễu."""
    for pt in points:
        if pt["is_noise"]:
            continue
        acc = pt.get("accuracy")
        if acc is not None and acc > config.ACCURACY_THRESHOLD_M:
            pt["is_noise"] = True
            pt["noise_reason"] = "accuracy"


# ============================================================
# Lớp B: Speed filter + duplicate timestamp
# ============================================================

def _filter_speed(points: list[dict]) -> None:
    """
    So sánh từng cặp điểm liên tiếp (không nhiễu):
    - Nếu time_delta < MIN_TIME_DELTA_S → duplicate/cache → đánh dấu điểm sau.
    - Nếu speed > SPEED_THRESHOLD_MS    → GPS jump → đánh dấu điểm sau.
    """
    # Lấy index các điểm chưa nhiễu để xét theo thứ tự
    clean_indices = [i for i, p in enumerate(points) if not p["is_noise"]]

    for k in range(1, len(clean_indices)):
        prev_idx = clean_indices[k - 1]
        curr_idx = clean_indices[k]

        prev = points[prev_idx]
        curr = points[curr_idx]

        dt: datetime = curr["timestamp"]
        dt_prev: datetime = prev["timestamp"]
        time_delta_s = (dt - dt_prev).total_seconds()

        # Duplicate / stale cache
        if time_delta_s < config.MIN_TIME_DELTA_S:
            curr["is_noise"] = True
            curr["noise_reason"] = "duplicate"
            continue

        # Speed filter
        dist_m = haversine_m(prev["lat"], prev["lng"], curr["lat"], curr["lng"])
        speed_ms = dist_m / time_delta_s
        if speed_ms > config.SPEED_THRESHOLD_MS:
            curr["is_noise"] = True
            curr["noise_reason"] = "speed"


# ============================================================
# Hard rule: Geofence
# ============================================================

def _filter_geofence(
    points: list[dict],
    center_lat: float,
    center_lng: float,
    max_radius_m: float,
) -> None:
    """Điểm nằm ngoài max_radius_m so với tâm quán → nhiễu geofence."""
    for pt in points:
        if pt["is_noise"]:
            continue
        dist = haversine_m(pt["lat"], pt["lng"], center_lat, center_lng)
        if dist > max_radius_m:
            pt["is_noise"] = True
            pt["noise_reason"] = "geofence"


# ============================================================
# Lớp C: Hampel Identifier (MAD-based sliding window)
# ============================================================

def _filter_hampel(points: list[dict]) -> None:
    """
    Phát hiện outlier cục bộ bằng Median Absolute Deviation trên cửa sổ trượt.
    Chỉ xét điểm chưa bị đánh là nhiễu bởi các lớp trước.
    Áp dụng độc lập trên trục lat và lng.
    """
    k = config.HAMPEL_WINDOW_K
    z_thresh = config.HAMPEL_Z_THRESHOLD

    # Chỉ lấy điểm sạch
    clean_indices = [i for i, p in enumerate(points) if not p["is_noise"]]
    n = len(clean_indices)

    if n < 2 * k + 1:
        # Không đủ điểm để chạy Hampel
        return

    lats = np.array([points[i]["lat"] for i in clean_indices])
    lngs = np.array([points[i]["lng"] for i in clean_indices])

    outlier_flags = np.zeros(n, dtype=bool)

    for dim_vals in (lats, lngs):
        for i in range(k, n - k):
            window = dim_vals[i - k: i + k + 1]
            median = np.median(window)
            mad = np.median(np.abs(window - median))
            scale = 1.4826 * mad  # hệ số chuẩn hóa MAD → std estimate

            # Nếu scale = 0 (tất cả điểm giống nhau) → không phải outlier
            if scale == 0:
                continue

            if abs(dim_vals[i] - median) > z_thresh * scale:
                outlier_flags[i] = True

    for j, original_idx in enumerate(clean_indices):
        if outlier_flags[j]:
            points[original_idx]["is_noise"] = True
            points[original_idx]["noise_reason"] = "hampel"


# ============================================================
# Helper: tách điểm sạch
# ============================================================

def get_clean_points(annotated_points: list[dict]) -> list[dict]:
    """Trả về danh sách chỉ các điểm không bị đánh dấu nhiễu."""
    return [p for p in annotated_points if not p["is_noise"]]
