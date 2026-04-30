"""
pipeline.py — Orchestrator: Gọi các bước theo thứ tự.

Điều phối toàn bộ pipeline 6 bước:
  Bước 1: Validation & Preprocessing
  Bước 2: Noise Filter
  Bước 3: ST-DBSCAN Clustering
  Bước 4: Feature Extraction
  Bước 5: Session Scoring
  Bước 6: Cafe Score Update (Bayesian Average)
"""

from __future__ import annotations

import time
from datetime import datetime

from scoring_engine import config
from scoring_engine.noise_filter import apply_noise_filter, get_clean_points
from scoring_engine.st_dbscan import run_st_dbscan
from scoring_engine.feature_extractor import extract_session_features
from scoring_engine.scorer import update_cafe_score, compute_session_score
from scoring_engine.utils.validators import (
    validate_payload,
    validate_and_parse_gps_points,
    normalize_cafe_history,
)


# ============================================================
# Public API — score_session
# ============================================================

def score_session(payload: dict) -> dict:
    """
    Chạy toàn bộ pipeline cho một session.

    Args:
        payload: dict theo input contract (scoring_engine_design.md mục 3.2).
            {
                session_id, device_id,
                cafe: {cafe_id, center_lat, center_lng, radius_meters},
                gps_points: [{lat, lng, accuracy, timestamp}, ...],
                cafe_history (optional): {...}
            }

    Returns:
        session_result dict theo output contract (mục 8.1).

    Raises:
        ValueError: nếu payload thiếu field bắt buộc hoặc dữ liệu không hợp lệ.
    """
    t0 = time.perf_counter()

    # ──────────────────────────────────────────────────────
    # Bước 1: Validation & Preprocessing
    # ──────────────────────────────────────────────────────
    validate_payload(payload)

    session_id = payload["session_id"]
    cafe       = payload["cafe"]
    cafe_id    = cafe["cafe_id"]

    # Parse + sort GPS points
    raw_gps = payload["gps_points"]

    if len(raw_gps) < config.MIN_RAW_POINTS:
        return _insufficient_session(session_id, cafe_id, len(raw_gps), t0)

    gps_points = validate_and_parse_gps_points(raw_gps)

    # Tính duration session từ đầu đến cuối
    session_duration_min = _compute_duration_min(gps_points)

    # ──────────────────────────────────────────────────────
    # Bước 2: Noise Filter
    # ──────────────────────────────────────────────────────
    annotated_points, filter_summary = apply_noise_filter(
        gps_points=gps_points,
        cafe_center_lat=cafe["center_lat"],
        cafe_center_lng=cafe["center_lng"],
        cafe_radius_m=float(cafe["radius_meters"]),
    )

    clean_pts = get_clean_points(annotated_points)

    # Nếu toàn bộ là nhiễu sau lọc
    if not clean_pts:
        return _build_session_result(
            session_id=session_id,
            cafe_id=cafe_id,
            filter_summary=filter_summary,
            dbscan_result=_null_dbscan("all_noise"),
            features={},
            session_duration_min=session_duration_min,
            t0=t0,
        )

    # ──────────────────────────────────────────────────────
    # Bước 3: ST-DBSCAN Clustering
    # ──────────────────────────────────────────────────────
    dbscan_result = run_st_dbscan(
        clean_points=clean_pts,
        cafe_center_lat=cafe["center_lat"],
        cafe_center_lng=cafe["center_lng"],
        cafe_radius_m=float(cafe["radius_meters"]),
    )

    # ──────────────────────────────────────────────────────
    # Bước 4: Feature Extraction
    # ──────────────────────────────────────────────────────
    features = extract_session_features(
        filter_summary=filter_summary,
        dbscan_result=dbscan_result,
        session_duration_min=session_duration_min,
    )

    processing_ms = int((time.perf_counter() - t0) * 1000)

    # ──────────────────────────────────────────────────────
    # Bước 5 output: build session result
    # ──────────────────────────────────────────────────────
    return _build_session_result(
        session_id=session_id,
        cafe_id=cafe_id,
        filter_summary=filter_summary,
        dbscan_result=dbscan_result,
        features=features,
        session_duration_min=session_duration_min,
        t0=t0,
    )


# ============================================================
# Public API — update_cafe_score
# ============================================================

def run_update_cafe_score(
    cafe_id: int,
    session_result: dict,
    cafe_history: dict | None,
    all_session_results: list[dict] | None = None,
) -> dict:
    """
    Bước 6: Cập nhật Bayesian cafe score sau khi có session mới.

    Args:
        cafe_id: ID quán.
        session_result: output của score_session().
        cafe_history: lịch sử quán từ backend (có thể None).
        all_session_results: nếu cung cấp → batch recalculation.

    Returns:
        cafe_result dict theo output contract (mục 8.2).
    """
    history = normalize_cafe_history(cafe_history)
    return update_cafe_score(
        cafe_id=cafe_id,
        session_result=session_result,
        cafe_history=history,
        all_session_results=all_session_results,
    )


# ============================================================
# Helpers
# ============================================================

def _compute_duration_min(gps_points: list[dict]) -> float:
    """Tính thời gian session từ điểm đầu đến điểm cuối (phút)."""
    if len(gps_points) < 2:
        return 0.0
    t_start: datetime = gps_points[0]["timestamp"]
    t_end: datetime   = gps_points[-1]["timestamp"]
    delta_s = (t_end - t_start).total_seconds()
    return max(0.0, delta_s / 60.0)


def _compute_session_only_score(features: dict) -> float:
    """
    [AI-5] Tính session_score từ features session-level (f2–f7, không có f1).

    f1 (study_rate) là metric đa session, không tồn tại ở session đơn lẻ.
    Các weight còn lại được normalize lại về tổng = 1.0.

    Returns:
        session_score ∈ [0.0, 1.0], làm tròn 4 chữ số.
    """
    w = config.WEIGHTS
    # Tổng weight không có f1
    total_w = (
        w["avg_stable_dur"]
        + w["spatial_stability"]
        + w["clean_data_rate"]
        + w["retention"]
        + w["cluster_purity"]
        + w["coverage_ratio"]
    )

    score = (
        w["avg_stable_dur"]    * features.get("f2_avg_stable_dur_norm", 0.0)
        + w["spatial_stability"] * features.get("f3_spatial_stability",   0.0)
        + w["clean_data_rate"]   * features.get("f4_clean_data_rate",      0.0)
        + w["retention"]         * features.get("f5_retention",            0.0)
        + w["cluster_purity"]    * features.get("f6_cluster_purity",       0.0)
        + w["coverage_ratio"]    * features.get("f7_coverage_ratio",       0.0)
    )

    normalized = score / total_w if total_w > 0 else 0.0
    return round(float(max(0.0, min(1.0, normalized))), 4)


def _build_session_result(
    session_id: str,
    cafe_id: int,
    filter_summary: dict,
    dbscan_result: dict,
    features: dict,
    session_duration_min: float,
    t0: float,
) -> dict:
    processing_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "session_id": session_id,
        "cafe_id":    cafe_id,

        # Noise Filter
        "total_gps_points":  filter_summary.get("total_points", 0),
        "clean_gps_points":  filter_summary.get("clean_count", 0),
        "noise_point_count": filter_summary.get("noise_count", 0),
        "clean_data_rate":   filter_summary.get("clean_rate", 0.0),

        # Study Detection
        "is_studying":                 dbscan_result.get("is_studying", False),
        "stable_duration_min":         dbscan_result.get("stable_duration_min", 0.0),
        "dominant_cluster_pct":        dbscan_result.get("dominant_cluster_pct", 0.0),
        "centroid_distance_to_cafe_m": dbscan_result.get("centroid_distance_to_cafe_m"),
        "is_within_cafe_radius":       dbscan_result.get("is_within_cafe_radius", False),
        "spatial_std_m":               dbscan_result.get("spatial_std_m"),
        "coverage_ratio":              dbscan_result.get("coverage_ratio", 0.0),
        "cluster_count":               dbscan_result.get("cluster_count", 0),
        "reason":                      dbscan_result.get("reason"),

        # Feature vector (logging/debug)
        "features": features,

        # [AI-5] Session score (f2–f7, không có f1 vì f1 là metric đa session)
        "session_score": _compute_session_only_score(features),

        # Meta
        "session_duration_min": round(session_duration_min, 1),
        "processing_time_ms":   processing_ms,
        "engine_version":       config.ENGINE_VERSION,
    }


def _insufficient_session(
    session_id: str,
    cafe_id: int,
    raw_count: int,
    t0: float,
) -> dict:
    """Session quá ít điểm GPS để xử lý."""
    processing_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "session_id": session_id,
        "cafe_id":    cafe_id,
        "total_gps_points":  raw_count,
        "clean_gps_points":  0,
        "noise_point_count": 0,
        "clean_data_rate":   0.0,
        "is_studying":       False,
        "stable_duration_min": 0.0,
        "dominant_cluster_pct": 0.0,
        "centroid_distance_to_cafe_m": None,
        "is_within_cafe_radius": False,
        "spatial_std_m": None,
        "coverage_ratio": 0.0,
        "cluster_count": 0,
        "reason": "insufficient_gps_points",
        "features": {},
        "session_score": 0.0,
        "session_duration_min": 0.0,
        "processing_time_ms": processing_ms,
        "engine_version": config.ENGINE_VERSION,
    }


def _null_dbscan(reason: str) -> dict:
    return {
        "cluster_labels": [],
        "dominant_cluster_id": None,
        "dominant_cluster_point_count": 0,
        "dominant_cluster_pct": 0.0,
        "dominant_cluster_centroid": None,
        "centroid_distance_to_cafe_m": None,
        "is_within_cafe_radius": False,
        "stable_duration_min": 0.0,
        "spatial_std_m": None,
        "coverage_ratio": 0.0,
        "cluster_count": 0,
        "is_studying": False,
        "reason": reason,
    }
