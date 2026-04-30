"""
feature_extractor.py — Bước 4: Trích xuất Feature Vector.

Tính 7 features từ kết quả noise_filter + st_dbscan để mô tả hành vi session.
Tất cả features được normalize về [0, 1].

Features:
  f1_study_rate        — tỷ lệ session is_studying (tính ở mức cafe, không phải session đơn)
  f2_avg_stable_dur    — thời gian ổn định chuẩn hóa
  f3_spatial_stability — nghịch đảo của spatial_std (môi trường yên tĩnh)
  f4_clean_data_rate   — tỷ lệ GPS sạch
  f5_retention         — không rời sớm
  f6_cluster_purity    — mật độ dominant cluster
  f7_coverage_ratio    — % thời gian trong cluster
"""

from scoring_engine import config


# ============================================================
# Session-level features (từ 1 session)
# ============================================================

def extract_session_features(
    filter_summary: dict,
    dbscan_result: dict,
    session_duration_min: float,
) -> dict:
    """
    Trích xuất feature vector của một session đơn lẻ.

    Args:
        filter_summary: output của noise_filter.apply_noise_filter()
            keys: {total_points, noise_count, clean_count, clean_rate}
        dbscan_result: output của st_dbscan.run_st_dbscan()
        session_duration_min: tổng thời gian session (phút).

    Returns:
        dict với các features đã normalize về [0, 1], phục vụ logging/debug.
        f1_study_rate KHÔNG có ở đây (tính ở mức tổng hợp cafe).
    """
    # f2: stable duration normalized
    stable_dur = dbscan_result.get("stable_duration_min", 0.0) or 0.0
    f2 = min(stable_dur / config.NORM_MAX_DURATION_MIN, 1.0)

    # f3: spatial stability = 1 - normalize(spatial_std)
    spatial_std = dbscan_result.get("spatial_std_m")
    if spatial_std is not None:
        f3 = 1.0 - min(spatial_std / config.NORM_MAX_SPATIAL_STD_M, 1.0)
    else:
        f3 = 0.0  # Không có cluster → kém ổn định

    # f4: clean data rate (đã ∈ [0, 1])
    f4 = float(filter_summary.get("clean_rate", 0.0))

    # f5: retention — session ≥ DROPOFF_THRESHOLD_MIN → không rời sớm
    is_dropoff = session_duration_min < config.DROPOFF_THRESHOLD_MIN
    f5 = 0.0 if is_dropoff else 1.0

    # f6: cluster purity = dominant_cluster_pct
    f6 = float(dbscan_result.get("dominant_cluster_pct", 0.0))

    # f7: coverage ratio (đã ∈ [0, 1])
    f7 = float(dbscan_result.get("coverage_ratio", 0.0))

    return {
        "f2_avg_stable_dur_norm": round(f2, 4),
        "f3_spatial_stability":   round(f3, 4),
        "f4_clean_data_rate":     round(f4, 4),
        "f5_retention":           round(f5, 4),
        "f6_cluster_purity":      round(f6, 4),
        "f7_coverage_ratio":      round(f7, 4),
    }


# ============================================================
# Cafe-level aggregate features (từ nhiều sessions)
# ============================================================

def aggregate_cafe_features(
    session_results: list[dict],
) -> dict:
    """
    Tổng hợp features từ nhiều session results để tính cafe score.

    Args:
        session_results: list các session_result dict (từ score_session).

    Returns:
        dict với 7 features ∈ [0, 1] để đưa vào weighted scoring.
    """
    if not session_results:
        return _zero_features()

    total = len(session_results)
    studying = [s for s in session_results if s.get("is_studying", False)]
    n_studying = len(studying)

    # f1: study rate
    f1 = n_studying / total if total > 0 else 0.0

    # f2: avg stable duration (chỉ tính session is_studying=True)
    if studying:
        avg_stable = sum(s.get("stable_duration_min", 0.0) for s in studying) / n_studying
        f2 = min(avg_stable / config.NORM_MAX_DURATION_MIN, 1.0)
    else:
        f2 = 0.0

    # f3: avg spatial stability (chỉ tính session is_studying=True)
    if studying:
        spatial_stds = [s.get("spatial_std_m") for s in studying if s.get("spatial_std_m") is not None]
        if spatial_stds:
            mean_std = sum(spatial_stds) / len(spatial_stds)
            f3 = 1.0 - min(mean_std / config.NORM_MAX_SPATIAL_STD_M, 1.0)
        else:
            f3 = 1.0  # Không có std → stable
    else:
        f3 = 0.0

    # f4: avg clean data rate (tất cả sessions)
    f4 = sum(s.get("clean_data_rate", 0.0) for s in session_results) / total

    # f5: retention = 1 - dropoff_rate
    dropoffs = sum(1 for s in session_results
                   if _get_duration(s) < config.DROPOFF_THRESHOLD_MIN)
    dropoff_rate = dropoffs / total
    f5 = 1.0 - dropoff_rate

    # f6: avg cluster purity (session is_studying=True)
    if studying:
        f6 = sum(s.get("dominant_cluster_pct", 0.0) for s in studying) / n_studying
    else:
        f6 = 0.0

    # f7: avg coverage ratio (session is_studying=True)
    if studying:
        f7 = sum(s.get("coverage_ratio", 0.0) for s in studying) / n_studying
    else:
        f7 = 0.0

    return {
        "f1_study_rate":        round(f1, 4),
        "f2_avg_stable_dur":    round(f2, 4),
        "f3_spatial_stability": round(f3, 4),
        "f4_clean_data_rate":   round(f4, 4),
        "f5_retention":         round(f5, 4),
        "f6_cluster_purity":    round(f6, 4),
        "f7_coverage_ratio":    round(f7, 4),
    }


def compute_aggregate_stats(session_results: list[dict]) -> dict:
    """
    Tính các chỉ số tổng hợp của cafe phục vụ output contract.
    """
    total = len(session_results)
    if total == 0:
        return {
            "total_sessions": 0,
            "studying_sessions": 0,
            "study_rate": 0.0,
            "avg_stable_duration_min": 0.0,
            "avg_spatial_std_m": None,
            "dropoff_count": 0,
            "dropoff_rate": 0.0,
        }

    studying = [s for s in session_results if s.get("is_studying", False)]
    n_studying = len(studying)

    avg_stable = (
        sum(s.get("stable_duration_min", 0.0) for s in studying) / n_studying
        if studying else 0.0
    )

    spatial_stds = [s.get("spatial_std_m") for s in studying if s.get("spatial_std_m") is not None]
    avg_spatial_std = (sum(spatial_stds) / len(spatial_stds)) if spatial_stds else None

    dropoffs = sum(1 for s in session_results if _get_duration(s) < config.DROPOFF_THRESHOLD_MIN)

    return {
        "total_sessions":           total,
        "studying_sessions":        n_studying,
        "study_rate":               round(n_studying / total, 4),
        "avg_stable_duration_min":  round(avg_stable, 1),
        "avg_spatial_std_m":        round(avg_spatial_std, 2) if avg_spatial_std is not None else None,
        "dropoff_count":            dropoffs,
        "dropoff_rate":             round(dropoffs / total, 4),
    }


# ============================================================
# Helpers
# ============================================================

def _zero_features() -> dict:
    return {k: 0.0 for k in [
        "f1_study_rate", "f2_avg_stable_dur", "f3_spatial_stability",
        "f4_clean_data_rate", "f5_retention", "f6_cluster_purity", "f7_coverage_ratio",
    ]}


def _get_duration(session_result: dict) -> float:
    """
    Lấy session_duration_min (tổng thời gian ngồi quán) để tính dropoff.

    [FIX AI-2] Đổi từ stable_duration_min → session_duration_min.
    Lý do: stable_duration_min = thời gian trong cluster (có thể ngắn dù ngồi lâu).
    Dropoff phải đo bằng tổng thời gian session thực tế.
    """
    return float(session_result.get("session_duration_min") or 0.0)
