"""
scorer.py — Bước 5–6: Session Scoring + Bayesian Cafe Score Update.

Bước 5: Weighted sum của 7 features → session_score ∈ [0, 1]
Bước 6: Bayesian Average blend session mới với prior lịch sử quán
        → cafe_score ∈ [0.0, 10.0]

Công thức Bayesian Average:
    S_cafe = (m × C + v × R) / (m + v)
    v = total studying sessions của quán
    R = raw_score × 10
    m = MIN_CONFIDENT_SESSIONS (prior weight)
    C = system_avg_score (prior)

Output keys khớp hoàn toàn với CafeScore ORM model (backend/app/models/cafe_score.py):
    cafe_id, computed_at,
    total_sessions, studying_sessions, study_rate,
    avg_stable_duration_min, avg_spatial_std_m,
    dropoff_count, dropoff_rate,
    behavior_score, has_enough_data,
    bayesian_m, prior_score, engine_version
"""

from __future__ import annotations

from datetime import datetime, timezone

from scoring_engine import config
from scoring_engine.feature_extractor import aggregate_cafe_features, compute_aggregate_stats


# ============================================================
# Bước 5: Session-level weighted score
# ============================================================

def compute_session_score(features_cafe: dict) -> float:
    """
    Tính raw_score của cafe từ feature vector đã aggregate.
    Weighted sum → [0, 1].

    Args:
        features_cafe: output của feature_extractor.aggregate_cafe_features()

    Returns:
        raw_score ∈ [0.0, 1.0]
    """
    w = config.WEIGHTS
    score = (
        w["study_rate"]         * features_cafe["f1_study_rate"]
        + w["avg_stable_dur"]   * features_cafe["f2_avg_stable_dur"]
        + w["spatial_stability"]* features_cafe["f3_spatial_stability"]
        + w["clean_data_rate"]  * features_cafe["f4_clean_data_rate"]
        + w["retention"]        * features_cafe["f5_retention"]
        + w["cluster_purity"]   * features_cafe["f6_cluster_purity"]
        + w["coverage_ratio"]   * features_cafe["f7_coverage_ratio"]
    )
    return float(max(0.0, min(1.0, score)))


# ============================================================
# Bước 6: Cafe-level Bayesian Average
# ============================================================

def bayesian_cafe_score(
    raw_score_0_1: float,
    studying_session_count: int,
    system_avg_score: float | None = None,
) -> float:
    """
    Bayesian Average: blend raw_score về prior khi ít data.

    S_cafe = (m × C + v × R) / (m + v)

    Args:
        raw_score_0_1: điểm thô [0, 1] từ weighted sum.
        studying_session_count: số session is_studying=True của quán.
        system_avg_score: điểm trung bình toàn hệ thống (prior C).

    Returns:
        cafe_score ∈ [0.0, 10.0], làm tròn 1 chữ số thập phân.
    """
    m = config.MIN_CONFIDENT_SESSIONS
    C = system_avg_score if system_avg_score is not None else config.DEFAULT_SYSTEM_AVG
    v = max(0, studying_session_count)
    R = raw_score_0_1 * config.SCORE_SCALE  # scale về [0, 10]

    if (m + v) == 0:
        score = C
    else:
        score = (m * C + v * R) / (m + v)

    score = max(0.0, min(config.SCORE_SCALE, score))
    return round(score, 1)


# ============================================================
# Public: update_cafe_score — Bước 6 đầy đủ
# ============================================================

def update_cafe_score(
    cafe_id: int,
    session_result: dict,
    cafe_history: dict | None,
    all_session_results: list[dict] | None = None,
) -> dict:
    """
    Cập nhật điểm quán sau khi có session mới.

    Hai chế độ:
    1. all_session_results được cung cấp → batch recalculation (ưu tiên).
    2. Chỉ session_result + cafe_history → incremental update.

    Output keys khớp với _persist_cafe_score() trong scoring_service.py:
        cafe_id, computed_at,
        total_sessions, studying_sessions, study_rate,
        avg_stable_duration_min, avg_spatial_std_m,
        dropoff_count, dropoff_rate,
        behavior_score, has_enough_data,
        bayesian_m, prior_score, engine_version

    Args:
        cafe_id: ID quán.
        session_result: output của score_session().
        cafe_history: dict từ backend (_get_cafe_history):
            {total_sessions_processed, studying_session_count,
             current_score, system_avg_score}. Có thể None.
        all_session_results: list tất cả session results (batch mode).

    Returns:
        dict cafe score result theo output contract.
    """
    now = datetime.now(timezone.utc).isoformat()

    if all_session_results is not None:
        return _compute_from_all_sessions(cafe_id, all_session_results, cafe_history, now)

    if cafe_history is None:
        return _compute_from_all_sessions(cafe_id, [session_result], None, now)

    return _compute_incremental(cafe_id, session_result, cafe_history, now)


# ============================================================
# Internal: batch computation
# ============================================================

def _compute_from_all_sessions(
    cafe_id: int,
    session_results: list[dict],
    cafe_history: dict | None,
    now: str,
) -> dict:
    """Tính lại toàn bộ từ list session results."""
    features = aggregate_cafe_features(session_results)
    stats    = compute_aggregate_stats(session_results)

    raw_score  = compute_session_score(features)
    system_avg = (
        float(cafe_history.get("system_avg_score") or config.DEFAULT_SYSTEM_AVG)
        if cafe_history else config.DEFAULT_SYSTEM_AVG
    )

    behavior_score = bayesian_cafe_score(
        raw_score_0_1=raw_score,
        studying_session_count=stats["studying_sessions"],
        system_avg_score=system_avg,
    )

    has_enough_data = stats["studying_sessions"] >= config.HAS_ENOUGH_DATA_THRESH

    return {
        # Identity
        "cafe_id":      cafe_id,
        "computed_at":  now,
        # Aggregate stats — khớp CafeScore model columns
        "total_sessions":           stats["total_sessions"],
        "studying_sessions":        stats["studying_sessions"],
        "study_rate":               stats["study_rate"],
        "avg_stable_duration_min":  stats["avg_stable_duration_min"],
        "avg_spatial_std_m":        stats["avg_spatial_std_m"],
        "dropoff_count":            stats["dropoff_count"],
        "dropoff_rate":             stats["dropoff_rate"],
        # Bayesian Score
        "behavior_score":   behavior_score,
        "has_enough_data":  has_enough_data,
        "bayesian_m":       config.MIN_CONFIDENT_SESSIONS,
        "prior_score":      system_avg,
        # Meta
        "engine_version":  config.ENGINE_VERSION,
    }


# ============================================================
# Internal: incremental computation
# ============================================================

def _compute_incremental(
    cafe_id: int,
    session_result: dict,
    cafe_history: dict,
    now: str,
) -> dict:
    """
    Incremental update: dùng aggregate statistics từ lịch sử + session mới.

    cafe_history keys (từ scoring_service._get_cafe_history):
        total_sessions_processed  : int   — tổng session đã xử lý
        studying_session_count    : int   — số session is_studying=True
        current_score             : float | None — behavior_score hiện tại
        system_avg_score          : float — prior C
        dropoff_count             : int   — [AI-3] số session dropoff lịch sử;
                                            PHẢI được thêm vào _get_cafe_history()
                                            ở scoring_service.py phía backend.
                                            Nếu thiếu → fallback 0 (mất lịch sử).
    """
    prev_total    = int(cafe_history.get("total_sessions_processed", 0))
    prev_studying = int(cafe_history.get("studying_session_count", 0))
    system_avg    = float(cafe_history.get("system_avg_score") or config.DEFAULT_SYSTEM_AVG)

    new_total    = prev_total + 1
    is_new_study = bool(session_result.get("is_studying", False))
    new_studying = prev_studying + (1 if is_new_study else 0)

    # f1: study rate mới
    f1 = new_studying / new_total if new_total > 0 else 0.0

    # Features từ session mới nếu is_studying, fallback về 0.0 nếu không
    # [FIX AI-1] NON_STUDY session không đóng góp feature dương — dùng 0.0 thay 0.5
    if is_new_study:
        stable_dur  = session_result.get("stable_duration_min", 0.0) or 0.0
        f2 = min(stable_dur / config.NORM_MAX_DURATION_MIN, 1.0)
        spatial_std = session_result.get("spatial_std_m") or 0.0
        f3 = 1.0 - min(spatial_std / config.NORM_MAX_SPATIAL_STD_M, 1.0)
        f6 = float(session_result.get("dominant_cluster_pct", 0.0))
        f7 = float(session_result.get("coverage_ratio", 0.0))
    else:
        # Session không học → không đóng góp feature học tập
        # f2 vẫn lấy từ prior để tránh mất info lịch sử hoàn toàn
        prev_score_0_10 = float(cafe_history.get("current_score") or config.DEFAULT_SYSTEM_AVG)
        f2 = min((prev_score_0_10 / config.SCORE_SCALE) * 0.8, 1.0)
        f3 = 0.0   # [FIX AI-1] was 0.5 — spatial stability không đáng tin khi không học
        f6 = 0.0   # [FIX AI-1] was 0.5 — cluster purity = 0 khi không có stable cluster
        f7 = 0.0   # [FIX AI-1] was 0.5 — coverage ratio = 0 khi không học

    f4 = float(session_result.get("clean_data_rate", 0.0))

    # [FIX AI-2] Dùng session_duration_min (tổng thời gian session) thay stable_duration_min
    # stable_duration_min = thời gian trong cluster → người ngồi 45' nhưng cluster 15' bị tính dropoff sai
    session_dur = float(session_result.get("session_duration_min") or 0.0)
    f5 = 0.0 if session_dur < config.DROPOFF_THRESHOLD_MIN else 1.0

    features = {
        "f1_study_rate":        round(f1, 4),
        "f2_avg_stable_dur":    round(f2, 4),
        "f3_spatial_stability": round(f3, 4),
        "f4_clean_data_rate":   round(f4, 4),
        "f5_retention":         round(f5, 4),
        "f6_cluster_purity":    round(f6, 4),
        "f7_coverage_ratio":    round(f7, 4),
    }

    raw_score = compute_session_score(features)
    behavior_score = bayesian_cafe_score(
        raw_score_0_1=raw_score,
        studying_session_count=new_studying,
        system_avg_score=system_avg,
    )

    has_enough_data = new_studying >= config.HAS_ENOUGH_DATA_THRESH

    # [FIX AI-2] Dùng session_duration_min thay stable_duration_min cho is_dropoff
    # [FIX AI-3] Cộng dồn dropoff_count từ lịch sử (prev_dropoffs) thay vì reset về 0/1
    #
    # AI-3 NOTE — cần Team Dev sync:
    # scoring_service._get_cafe_history() phải trả thêm key "dropoff_count": int
    # để incremental mode tích lũy được lịch sử. Nếu key không có → fallback về 0
    # (an toàn nhưng mất lịch sử dropoff trước đó, giống bug cũ).
    session_dur_for_dropoff = float(session_result.get("session_duration_min") or 0.0)
    is_dropoff    = session_dur_for_dropoff < config.DROPOFF_THRESHOLD_MIN
    prev_dropoffs = int(cafe_history.get("dropoff_count", 0))
    new_dropoffs  = prev_dropoffs + (1 if is_dropoff else 0)

    return {
        # Identity
        "cafe_id":      cafe_id,
        "computed_at":  now,
        # Aggregate stats — khớp CafeScore model columns
        "total_sessions":           new_total,
        "studying_sessions":        new_studying,
        "study_rate":               round(f1, 4),
        "avg_stable_duration_min":  None,   # incremental: không đủ data để avg
        "avg_spatial_std_m":        None,
        "dropoff_count":            new_dropoffs,
        "dropoff_rate":             round(new_dropoffs / new_total, 4) if new_total else 0.0,
        # Bayesian Score
        "behavior_score":   behavior_score,
        "has_enough_data":  has_enough_data,
        "bayesian_m":       config.MIN_CONFIDENT_SESSIONS,
        "prior_score":      system_avg,
        # Meta
        "engine_version":   config.ENGINE_VERSION,
    }
