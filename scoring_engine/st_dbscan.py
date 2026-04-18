"""
st_dbscan.py — Bước 3: ST-DBSCAN Clustering + Stay-point Detection.

Phát hiện "điểm dừng" (stay-point) — vị trí người dùng ở lại lâu —
bằng cách phân cụm đồng thời cả không gian lẫn thời gian.

Lý do dùng ST-DBSCAN thay vì DBSCAN thường:
- DBSCAN thường gộp nhầm hai lần học cách nhau nhiều giờ cùng chỗ.
- ST-DBSCAN thêm điều kiện eps_temporal: hai điểm chỉ cùng cluster
  khi cả khoảng cách lẫn khoảng thời gian đều trong ngưỡng.
"""

from __future__ import annotations

import numpy as np
from sklearn.cluster import DBSCAN

from scoring_engine import config
from scoring_engine.utils.haversine import haversine_m


# ============================================================
# Public API
# ============================================================

def run_st_dbscan(
    clean_points: list[dict],
    cafe_center_lat: float,
    cafe_center_lng: float,
    cafe_radius_m: float,
) -> dict:
    """
    Chạy ST-DBSCAN trên danh sách điểm GPS sạch.

    Args:
        clean_points: list dict {lat, lng, timestamp (datetime)}.
                      Chỉ điểm is_noise=False.
        cafe_center_lat, cafe_center_lng: tọa độ trung tâm quán.
        cafe_radius_m: bán kính quán (mét).

    Returns:
        dict kết quả study detection (xem phần Output Contract trong design doc).
    """
    n = len(clean_points)

    # Kiểm tra session quá ngắn (trước khi clustering)
    if n < config.MIN_CLEAN_POINTS:
        return _not_studying("too_short", n)

    # Tính tổng thời gian session (giây) từ điểm đầu đến điểm cuối
    t_start = clean_points[0]["timestamp"].timestamp()
    t_end   = clean_points[-1]["timestamp"].timestamp()
    total_duration_s = t_end - t_start

    if total_duration_s / 60.0 < config.MIN_STABLE_DURATION_MIN:
        return _not_studying("too_short", n)

    # Build feature matrix & run ST-DBSCAN
    labels = _run_clustering(clean_points)

    unique_labels = set(labels) - {-1}
    if not unique_labels:
        return _not_studying("no_cluster", n)

    # Tìm dominant cluster
    dominant = _find_dominant_cluster(clean_points, labels, unique_labels)

    if dominant is None:
        return _not_studying("no_dominant_cluster", n)

    cluster_id         = dominant["cluster_id"]
    cluster_points     = dominant["points"]
    cluster_count_pts  = len(cluster_points)
    dominant_pct       = cluster_count_pts / n

    # Kiểm tra dominant_cluster_pct ≥ ngưỡng
    if dominant_pct < config.DOMINANT_CLUSTER_PCT:
        return _not_studying("low_cluster_purity", n)

    # Tính centroid của dominant cluster
    centroid_lat = float(np.mean([p["lat"] for p in cluster_points]))
    centroid_lng = float(np.mean([p["lng"] for p in cluster_points]))

    # Kiểm tra centroid có trong bán kính quán
    dist_to_cafe = haversine_m(centroid_lat, centroid_lng, cafe_center_lat, cafe_center_lng)
    effective_radius = cafe_radius_m + config.RADIUS_BUFFER_M
    is_within_radius = dist_to_cafe <= effective_radius

    if not is_within_radius:
        return _not_studying("outside_cafe_radius", n)

    # Tính stable_duration = span thời gian của cluster (phút)
    ts_values = sorted(p["timestamp"].timestamp() for p in cluster_points)
    stable_duration_min = (ts_values[-1] - ts_values[0]) / 60.0

    if stable_duration_min < config.MIN_STABLE_DURATION_MIN:
        return _not_studying("too_short", n)

    # Tính spatial_std (độ phân tán khoảng cách tới centroid)
    dists_to_centroid = [
        haversine_m(p["lat"], p["lng"], centroid_lat, centroid_lng)
        for p in cluster_points
    ]
    spatial_std_m = float(np.std(dists_to_centroid)) if len(dists_to_centroid) > 1 else 0.0

    if spatial_std_m > config.MAX_SPATIAL_STD_M:
        return _not_studying("high_spatial_std", n)

    # Tính coverage_ratio = % thời gian trong cluster / tổng session
    coverage_ratio = _compute_coverage_ratio(cluster_points, total_duration_s)

    # Số lượng cluster khác nhau (không tính noise)
    cluster_count = len(unique_labels)

    return {
        "cluster_labels":               labels.tolist(),
        "dominant_cluster_id":          int(cluster_id),
        "dominant_cluster_point_count": cluster_count_pts,
        "dominant_cluster_pct":         round(dominant_pct, 4),
        "dominant_cluster_centroid": {
            "lat": round(centroid_lat, 6),
            "lng": round(centroid_lng, 6),
        },
        "centroid_distance_to_cafe_m":  round(dist_to_cafe, 2),
        "is_within_cafe_radius":        True,
        "stable_duration_min":          round(stable_duration_min, 1),
        "spatial_std_m":                round(spatial_std_m, 2),
        "coverage_ratio":               round(coverage_ratio, 4),
        "cluster_count":                cluster_count,
        "is_studying":                  True,
        "reason":                       None,
    }


# ============================================================
# ST-DBSCAN Implementation
# ============================================================

def _run_clustering(clean_points: list[dict]) -> np.ndarray:
    """
    Tạo feature matrix và chạy DBSCAN với custom ST-distance metric.

    Custom metric: max(spatial_dist / eps_spatial, temporal_dist / eps_temporal)
    → eps=1.0 trong DBSCAN không gian chuẩn hóa.
    """
    n = len(clean_points)

    # Precompute timestamp (Unix seconds)
    ts_arr  = np.array([p["timestamp"].timestamp() for p in clean_points])
    lat_arr = np.array([p["lat"] for p in clean_points])
    lng_arr = np.array([p["lng"] for p in clean_points])

    eps_s = config.EPS_SPATIAL_M
    eps_t = config.EPS_TEMPORAL_S

    # Build distance matrix (n×n) — O(n²) nhưng session max ~480 điểm → đủ nhanh
    dist_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            spatial  = haversine_m(lat_arr[i], lng_arr[i], lat_arr[j], lng_arr[j])
            temporal = abs(ts_arr[i] - ts_arr[j])
            # Normalize và lấy max (điều kiện AND: phải thỏa cả spatial lẫn temporal)
            d = max(spatial / eps_s, temporal / eps_t)
            dist_matrix[i, j] = d
            dist_matrix[j, i] = d

    db = DBSCAN(
        eps=1.0,
        min_samples=config.DBSCAN_MIN_SAMPLES,
        metric="precomputed",
    )
    labels = db.fit_predict(dist_matrix)
    return labels


# ============================================================
# Dominant cluster selection
# ============================================================

def _find_dominant_cluster(
    clean_points: list[dict],
    labels: np.ndarray,
    unique_labels: set,
) -> dict | None:
    """
    Tìm dominant cluster:
    1. Cluster chứa nhiều điểm nhất.
    2. Tie-break: chọn cluster có centroid gần tâm quán nhất
       (không cần tọa độ tâm quán ở đây — sẽ kiểm tra bên ngoài).
    """
    best_id = None
    best_count = 0

    for cid in unique_labels:
        count = int(np.sum(labels == cid))
        if count > best_count:
            best_count = count
            best_id = cid

    if best_id is None:
        return None

    cluster_pts = [clean_points[i] for i, lbl in enumerate(labels) if lbl == best_id]
    return {"cluster_id": best_id, "points": cluster_pts}


# ============================================================
# Coverage ratio
# ============================================================

def _compute_coverage_ratio(cluster_points: list[dict], total_duration_s: float) -> float:
    """
    Tính tỷ lệ thời gian người dùng ở trong cluster / tổng session.
    Tính bằng span thời gian của cluster.
    """
    if total_duration_s <= 0:
        return 0.0

    ts_sorted = sorted(p["timestamp"].timestamp() for p in cluster_points)
    cluster_span_s = ts_sorted[-1] - ts_sorted[0]

    return min(cluster_span_s / total_duration_s, 1.0)


# ============================================================
# Helper: kết quả NOT STUDYING
# ============================================================

def _not_studying(reason: str, n_clean: int) -> dict:
    """Tạo dict kết quả cho session không được coi là đang học."""
    return {
        "cluster_labels":               [],
        "dominant_cluster_id":          None,
        "dominant_cluster_point_count": 0,
        "dominant_cluster_pct":         0.0,
        "dominant_cluster_centroid":    None,
        "centroid_distance_to_cafe_m":  None,
        "is_within_cafe_radius":        False,
        "stable_duration_min":          0.0,
        "spatial_std_m":                None,
        "coverage_ratio":               0.0,
        "cluster_count":                0,
        "is_studying":                  False,
        "reason":                       reason,
    }
