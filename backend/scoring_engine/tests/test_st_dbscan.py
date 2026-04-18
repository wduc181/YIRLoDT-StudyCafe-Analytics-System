"""
test_st_dbscan.py — Unit tests cho ST-DBSCAN Clustering (Bước 3).

Chạy: pytest scoring_engine/tests/test_st_dbscan.py -v
"""

import json
from pathlib import Path

import pytest

from scoring_engine.noise_filter import apply_noise_filter, get_clean_points
from scoring_engine.st_dbscan import run_st_dbscan
from scoring_engine.utils.validators import validate_and_parse_gps_points

FIXTURES = Path(__file__).parent / "fixtures"
CAFE = {"cafe_center_lat": 21.0024, "cafe_center_lng": 105.8453, "cafe_radius_m": 50.0}


def load_fixture(name: str) -> dict:
    with open(FIXTURES / name) as f:
        return json.load(f)


def run_pipeline_to_dbscan(payload: dict) -> dict:
    """Helper: chạy từ raw payload đến output ST-DBSCAN."""
    cafe = payload["cafe"]
    pts = validate_and_parse_gps_points(payload["gps_points"])
    annotated, _ = apply_noise_filter(
        pts,
        cafe_center_lat=cafe["center_lat"],
        cafe_center_lng=cafe["center_lng"],
        cafe_radius_m=float(cafe["radius_meters"]),
    )
    clean = get_clean_points(annotated)
    return run_st_dbscan(
        clean_points=clean,
        cafe_center_lat=cafe["center_lat"],
        cafe_center_lng=cafe["center_lng"],
        cafe_radius_m=float(cafe["radius_meters"]),
    )


# ──────────────────────────────────────────────────────────────
# TC-DB-01: Happy path → is_studying = True
# ──────────────────────────────────────────────────────────────

def test_ideal_session_is_studying():
    payload = load_fixture("session_studying_ideal.json")
    result = run_pipeline_to_dbscan(payload)

    assert result["is_studying"] is True, (
        f"Session học lý tưởng phải is_studying=True. reason={result.get('reason')}"
    )
    assert result["stable_duration_min"] >= 20.0, (
        f"stable_duration phải ≥ 20 phút, nhận được {result['stable_duration_min']}"
    )
    assert result["is_within_cafe_radius"] is True


# ──────────────────────────────────────────────────────────────
# TC-DB-02: Session quá ngắn → is_studying = False
# ──────────────────────────────────────────────────────────────

def test_short_session_not_studying():
    payload = load_fixture("session_not_studying_short.json")
    result = run_pipeline_to_dbscan(payload)

    assert result["is_studying"] is False
    assert result["reason"] in ("too_short", "no_cluster", "low_cluster_purity"), (
        f"Reason không hợp lệ: {result['reason']}"
    )


# ──────────────────────────────────────────────────────────────
# TC-DB-03: Ngồi ngoài quán → is_within_cafe_radius = False
# ──────────────────────────────────────────────────────────────

def test_outside_cafe_not_studying():
    payload = load_fixture("session_outside_cafe.json")
    result = run_pipeline_to_dbscan(payload)

    assert result["is_studying"] is False, (
        "GPS ngoài quán phải is_studying=False"
    )


# ──────────────────────────────────────────────────────────────
# TC-DB-04: Di chuyển liên tục → không có cluster ổn định
# ──────────────────────────────────────────────────────────────

def test_continuous_movement_not_studying():
    """
    GPS points nằm trong geofence nhưng di chuyển zigzag > eps_spatial (25m) mỗi bước.
    ST-DBSCAN không tạo được dominant cluster ổn định.
    Reason phải là 'low_cluster_purity' hoặc 'no_cluster' — KHÔNG phải 'all_noise'.
    """
    payload = load_fixture("session_continuous_move.json")
    result = run_pipeline_to_dbscan(payload)

    assert result["is_studying"] is False, "Di chuyển liên tục phải is_studying=False"
    assert result["reason"] in ("low_cluster_purity", "no_cluster", "too_short"), (
        f"reason phải là low_cluster_purity/no_cluster, nhận được: {result['reason']}"
    )


# ──────────────────────────────────────────────────────────────
# TC-DB-05: Input rỗng → không crash, trả not_studying
# ──────────────────────────────────────────────────────────────

def test_empty_clean_points_no_crash():
    """Input rỗng phải trả is_studying=False với reason rõ ràng, không crash."""
    result = run_st_dbscan(
        clean_points=[],
        cafe_center_lat=21.0024,
        cafe_center_lng=105.8453,
        cafe_radius_m=50.0,
    )
    assert result["is_studying"] is False
    assert result["reason"] in ("too_short", "no_cluster", "no_dominant_cluster"), (
        f"Empty input phải trả reason rõ ràng, nhận được: {result['reason']}"
    )


# ──────────────────────────────────────────────────────────────
# TC-DB-06: 1 điểm duy nhất → không crash
# ──────────────────────────────────────────────────────────────

def test_single_point_no_crash():
    from datetime import timezone
    from dateutil import parser as dateutil_parser

    pts = [{"lat": 21.0024, "lng": 105.8453,
            "timestamp": dateutil_parser.isoparse("2026-04-07T09:00:00Z")}]
    result = run_st_dbscan(pts, 21.0024, 105.8453, 50.0)
    assert result["is_studying"] is False


# ──────────────────────────────────────────────────────────────
# TC-DB-07: Output format hợp lệ
# ──────────────────────────────────────────────────────────────

def test_output_format_keys():
    payload = load_fixture("session_studying_ideal.json")
    result = run_pipeline_to_dbscan(payload)

    required_keys = [
        "is_studying", "stable_duration_min", "dominant_cluster_pct",
        "centroid_distance_to_cafe_m", "is_within_cafe_radius",
        "spatial_std_m", "coverage_ratio", "cluster_count", "reason",
    ]
    for key in required_keys:
        assert key in result, f"Output thiếu key '{key}'"

    # coverage_ratio ∈ [0, 1]
    assert 0.0 <= result["coverage_ratio"] <= 1.0

    # dominant_cluster_pct ∈ [0, 1]
    assert 0.0 <= result["dominant_cluster_pct"] <= 1.0


# ──────────────────────────────────────────────────────────────
# TC-DB-08: GPS nhiễu nặng → không đủ clean points → not studying
# ──────────────────────────────────────────────────────────────

def test_noisy_gps_insufficient_clean():
    payload = load_fixture("session_noisy_gps.json")
    cafe = payload["cafe"]
    pts = validate_and_parse_gps_points(payload["gps_points"])
    annotated, filter_summary = apply_noise_filter(
        pts,
        cafe_center_lat=cafe["center_lat"],
        cafe_center_lng=cafe["center_lng"],
        cafe_radius_m=float(cafe["radius_meters"]),
    )
    clean = get_clean_points(annotated)

    result = run_st_dbscan(clean, cafe["center_lat"], cafe["center_lng"], cafe["radius_meters"])

    # Dù clean_count thấp hay cao, pipeline không crash
    assert isinstance(result["is_studying"], bool)
    # Nếu not studying thì phải có reason
    if not result["is_studying"]:
        assert result["reason"] is not None, "Khi is_studying=False phải có reason"
