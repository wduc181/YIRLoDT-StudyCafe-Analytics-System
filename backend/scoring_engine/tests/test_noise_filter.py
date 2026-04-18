"""
test_noise_filter.py — Unit tests cho Noise Filter (Bước 2).

Chạy: pytest scoring_engine/tests/test_noise_filter.py -v
"""

import json
from pathlib import Path
from datetime import datetime, timezone

import pytest

from scoring_engine.noise_filter import apply_noise_filter, get_clean_points
from scoring_engine.utils.validators import validate_and_parse_gps_points

FIXTURES = Path(__file__).parent / "fixtures"
CAFE = {"center_lat": 21.0024, "center_lng": 105.8453, "radius_meters": 50}


def load_fixture(name: str) -> dict:
    with open(FIXTURES / name) as f:
        return json.load(f)


def parse_points(payload: dict) -> list[dict]:
    return validate_and_parse_gps_points(payload["gps_points"])


# ──────────────────────────────────────────────────────────────
# TC-NF-01: GPS tốt → clean_rate cao
# ──────────────────────────────────────────────────────────────

def test_clean_session_high_clean_rate():
    payload = load_fixture("session_studying_ideal.json")
    pts = parse_points(payload)
    _, summary = apply_noise_filter(pts, **CAFE)

    assert summary["clean_rate"] >= 0.85, (
        f"Session GPS tốt phải có clean_rate ≥ 0.85, nhận được {summary['clean_rate']}"
    )
    assert summary["total_points"] == len(pts)
    assert summary["noise_count"] + summary["clean_count"] == summary["total_points"]


# ──────────────────────────────────────────────────────────────
# TC-NF-02: GPS nhiễu nặng → clean_rate thấp
# ──────────────────────────────────────────────────────────────

def test_noisy_session_low_clean_rate():
    payload = load_fixture("session_noisy_gps.json")
    pts = parse_points(payload)
    annotated, summary = apply_noise_filter(pts, **CAFE)

    # Nhiều điểm accuracy > 50 → bị lọc lớp A
    assert summary["noise_count"] > 0, "Phải có ít nhất 1 điểm bị lọc"
    assert summary["clean_rate"] < 0.60, (
        f"Session nhiễu nặng phải có clean_rate < 0.60, nhận được {summary['clean_rate']}"
    )


# ──────────────────────────────────────────────────────────────
# TC-NF-03: Điểm nằm ngoài 2× radius → geofence filter
# ──────────────────────────────────────────────────────────────

def test_outside_cafe_filtered_by_geofence():
    payload = load_fixture("session_outside_cafe.json")
    pts = parse_points(payload)
    annotated, summary = apply_noise_filter(pts, **CAFE)

    geofence_filtered = [p for p in annotated if p.get("noise_reason") == "geofence"]
    assert len(geofence_filtered) > 0, (
        "Điểm GPS cách tâm quán >100m phải bị đánh dấu geofence"
    )


# ──────────────────────────────────────────────────────────────
# TC-NF-04: accuracy = null → bỏ lớp A, vẫn chạy B + C
# ──────────────────────────────────────────────────────────────

def test_null_accuracy_skips_layer_a():
    pts_raw = [
        {"lat": 21.0024, "lng": 105.8453, "accuracy": None, "timestamp": "2026-04-07T09:00:00Z"},
        {"lat": 21.0024, "lng": 105.8454, "accuracy": None, "timestamp": "2026-04-07T09:01:00Z"},
        {"lat": 21.0025, "lng": 105.8453, "accuracy": None, "timestamp": "2026-04-07T09:02:00Z"},
    ]
    pts = validate_and_parse_gps_points(pts_raw)
    annotated, summary = apply_noise_filter(pts, **CAFE)

    # Không có điểm nào bị lọc bởi accuracy
    accuracy_filtered = [p for p in annotated if p.get("noise_reason") == "accuracy"]
    assert len(accuracy_filtered) == 0


# ──────────────────────────────────────────────────────────────
# TC-NF-05: Điểm di chuyển tốc độ > 30km/h → speed filter
# ──────────────────────────────────────────────────────────────

def test_speed_filter_catches_gps_jump():
    pts_raw = [
        # Điểm 1: tại quán
        {"lat": 21.0024, "lng": 105.8453, "accuracy": 12.0, "timestamp": "2026-04-07T09:00:00Z"},
        # Điểm 2: nhảy ~500m trong 1 phút → speed ≈ 8.33 m/s = đúng ngưỡng; dùng ~700m để chắc chắn vượt
        {"lat": 21.0087, "lng": 105.8453, "accuracy": 12.0, "timestamp": "2026-04-07T09:01:00Z"},
        # Điểm 3: quay về
        {"lat": 21.0025, "lng": 105.8453, "accuracy": 12.0, "timestamp": "2026-04-07T09:02:00Z"},
    ]
    pts = validate_and_parse_gps_points(pts_raw)
    annotated, _ = apply_noise_filter(pts, **CAFE)

    speed_filtered = [p for p in annotated if p.get("noise_reason") == "speed"]
    assert len(speed_filtered) >= 1, "Điểm nhảy nhanh phải bị speed filter bắt"


# ──────────────────────────────────────────────────────────────
# TC-NF-06: Tất cả điểm là nhiễu → không crash
# ──────────────────────────────────────────────────────────────

def test_all_noise_does_not_crash():
    pts_raw = [
        {"lat": 21.0024, "lng": 105.8453, "accuracy": 500.0, "timestamp": "2026-04-07T09:00:00Z"},
        {"lat": 21.0024, "lng": 105.8454, "accuracy": 400.0, "timestamp": "2026-04-07T09:01:00Z"},
        {"lat": 21.0025, "lng": 105.8453, "accuracy": 300.0, "timestamp": "2026-04-07T09:02:00Z"},
    ]
    pts = validate_and_parse_gps_points(pts_raw)
    annotated, summary = apply_noise_filter(pts, **CAFE)

    # Không crash
    assert summary["clean_count"] == 0 or summary["clean_count"] >= 0  # luôn đúng, quan trọng là không raise
    clean = get_clean_points(annotated)
    assert isinstance(clean, list)


# ──────────────────────────────────────────────────────────────
# TC-NF-07: Output format hợp lệ
# ──────────────────────────────────────────────────────────────

def test_output_format():
    payload = load_fixture("session_studying_ideal.json")
    pts = parse_points(payload)
    annotated, summary = apply_noise_filter(pts, **CAFE)

    # Kiểm tra summary keys
    for key in ("total_points", "noise_count", "clean_count", "clean_rate"):
        assert key in summary, f"summary thiếu key '{key}'"

    # Kiểm tra từng điểm có đủ trường
    for pt in annotated:
        assert "is_noise" in pt
        assert "noise_reason" in pt
        assert isinstance(pt["is_noise"], bool)

    # clean_rate ∈ [0, 1]
    assert 0.0 <= summary["clean_rate"] <= 1.0
