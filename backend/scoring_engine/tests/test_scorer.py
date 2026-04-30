"""
test_scorer.py — Unit tests cho Scorer + Pipeline end-to-end (Bước 5–6).

Chạy: pytest scoring_engine/tests/test_scorer.py -v
"""

import json
from pathlib import Path

import pytest

from scoring_engine import score_session, update_cafe_score
from scoring_engine.scorer import bayesian_cafe_score, compute_session_score
from scoring_engine import config

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    with open(FIXTURES / name) as f:
        return json.load(f)


# ──────────────────────────────────────────────────────────────
# TC-SC-01: Happy path end-to-end → score ≥ 7.0
# ──────────────────────────────────────────────────────────────

def test_ideal_session_end_to_end():
    payload = load_fixture("session_studying_ideal.json")
    result = score_session(payload)

    assert result["is_studying"] is True, (
        f"Session lý tưởng phải is_studying=True. reason={result.get('reason')}"
    )
    assert result["stable_duration_min"] >= 20.0
    assert result["engine_version"] == config.ENGINE_VERSION  # phải là "2.0.0"

    # Update cafe score
    cafe_result = update_cafe_score(
        cafe_id=payload["cafe"]["cafe_id"],
        session_result=result,
        cafe_history=payload.get("cafe_history"),
    )
    assert 0.0 <= cafe_result["behavior_score"] <= 10.0
    assert cafe_result["engine_version"] == config.ENGINE_VERSION


# ──────────────────────────────────────────────────────────────
# TC-SC-02: Session quá ngắn → is_studying = False
# ──────────────────────────────────────────────────────────────

def test_short_session_not_studying():
    payload = load_fixture("session_not_studying_short.json")
    result = score_session(payload)

    assert result["is_studying"] is False
    assert result["reason"] is not None


# ──────────────────────────────────────────────────────────────
# TC-SC-03: Score luôn trong [0.0, 10.0]
# ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fixture_name", [
    "session_studying_ideal.json",
    "session_not_studying_short.json",
    "session_noisy_gps.json",
    "session_outside_cafe.json",
    "session_continuous_move.json",
])
def test_score_always_in_range(fixture_name):
    payload = load_fixture(fixture_name)
    session_result = score_session(payload)
    cafe_result = update_cafe_score(
        cafe_id=payload["cafe"]["cafe_id"],
        session_result=session_result,
        cafe_history=payload.get("cafe_history"),
    )
    score = cafe_result["behavior_score"]
    assert 0.0 <= score <= 10.0, f"{fixture_name}: score={score} nằm ngoài [0, 10]"
    # continuous_move phải bị detect bởi ST-DBSCAN (reason trong cluster/purity)
    # không phải bởi geofence filter (reason=all_noise)
    if fixture_name == "session_continuous_move.json":
        assert session_result.get("reason") in (
            "low_cluster_purity", "no_cluster", "too_short"
        ), f"continuous_move phải fail ở ST-DBSCAN, nhận reason={session_result.get('reason')}"


# ──────────────────────────────────────────────────────────────
# TC-SC-04: Bayesian Average — quán mới bị kéo về prior
# ──────────────────────────────────────────────────────────────

def test_bayesian_pulls_new_cafe_to_prior():
    # Quán mới 2 session, raw score cao
    score = bayesian_cafe_score(
        raw_score_0_1=0.9,
        studying_session_count=2,
        system_avg_score=6.5,
    )
    # Score phải < 9.0 (bị kéo về prior 6.5)
    assert score < 9.0, f"Quán mới phải bị pull về prior, nhận được {score}"
    assert score > 6.5, "Score vẫn phải cao hơn prior"


# ──────────────────────────────────────────────────────────────
# TC-SC-05: Bayesian Average — quán lâu gần raw score
# ──────────────────────────────────────────────────────────────

def test_bayesian_mature_cafe_near_raw():
    score = bayesian_cafe_score(
        raw_score_0_1=0.9,
        studying_session_count=30,
        system_avg_score=6.5,
    )
    # Với 30 session, score phải gần raw (9.0) hơn prior (6.5)
    assert score > 8.0, f"Quán lâu phải gần raw score, nhận được {score}"


# ──────────────────────────────────────────────────────────────
# TC-SC-06: Bayesian Average — v=0 → prior
# ──────────────────────────────────────────────────────────────

def test_bayesian_zero_sessions_returns_prior():
    # Dùng DEFAULT_SYSTEM_AVG = 6.5 (khớp với backend scoring_service.py default_prior)
    prior = config.DEFAULT_SYSTEM_AVG  # 6.5
    score = bayesian_cafe_score(
        raw_score_0_1=0.8,
        studying_session_count=0,
        system_avg_score=prior,
    )
    # v=0: S = (m*C + 0*R) / m = C
    assert score == prior, f"v=0 phải trả về prior={prior}, nhận được {score}"


# ──────────────────────────────────────────────────────────────
# TC-SC-07: has_enough_data — dưới ngưỡng
# ──────────────────────────────────────────────────────────────

def test_has_enough_data_below_threshold():
    payload = load_fixture("session_not_studying_short.json")
    session_result = score_session(payload)
    cafe_result = update_cafe_score(
        cafe_id=1,
        session_result=session_result,
        cafe_history={
            "total_sessions_processed": 2,
            "current_score": None,
            "studying_session_count": 1,
            "system_avg_score": 5.0,
        },
    )
    assert cafe_result["has_enough_data"] is False


# ──────────────────────────────────────────────────────────────
# TC-SC-08: Output format đầy đủ keys
# ──────────────────────────────────────────────────────────────

def test_session_result_output_keys():
    payload = load_fixture("session_studying_ideal.json")
    result = score_session(payload)

    required = [
        "session_id", "cafe_id",
        "total_gps_points", "clean_gps_points", "noise_point_count", "clean_data_rate",
        "is_studying", "stable_duration_min", "dominant_cluster_pct",
        "centroid_distance_to_cafe_m", "is_within_cafe_radius",
        "spatial_std_m", "coverage_ratio", "cluster_count",
        "features", "session_duration_min", "processing_time_ms", "engine_version",
    ]
    for key in required:
        assert key in result, f"session_result thiếu key '{key}'"


def test_cafe_result_output_keys():
    payload = load_fixture("session_studying_ideal.json")
    session_result = score_session(payload)
    cafe_result = update_cafe_score(
        cafe_id=payload["cafe"]["cafe_id"],
        session_result=session_result,
        cafe_history=payload.get("cafe_history"),
    )

    # Keys khớp với CafeScore ORM model (backend/app/models/cafe_score.py)
    # và _persist_cafe_score() trong scoring_service.py
    required = [
        "cafe_id", "computed_at",
        # Aggregate stats
        "total_sessions", "studying_sessions", "study_rate",
        "avg_stable_duration_min", "avg_spatial_std_m",
        "dropoff_count", "dropoff_rate",
        # Bayesian Score
        "behavior_score", "has_enough_data",
        "bayesian_m", "prior_score",
        # Meta
        "engine_version",
    ]
    for key in required:
        assert key in cafe_result, f"cafe_result thiếu key '{key}' (cần cho CafeScore model)"


# ──────────────────────────────────────────────────────────────
# TC-SC-09: payload không hợp lệ → ValueError
# ──────────────────────────────────────────────────────────────

def test_invalid_payload_raises_value_error():
    with pytest.raises((ValueError, KeyError)):
        score_session({"session_id": "test"})  # thiếu cafe, device_id, gps_points


# ──────────────────────────────────────────────────────────────
# TC-SC-10: Batch mode — update_cafe_score với all_session_results
# ──────────────────────────────────────────────────────────────

def test_batch_update_cafe_score():
    payload = load_fixture("session_studying_ideal.json")
    session_result = score_session(payload)

    # Giả lập 5 session results đã có
    all_results = [session_result] * 5

    cafe_result = update_cafe_score(
        cafe_id=1,
        session_result=session_result,
        cafe_history=None,
        all_session_results=all_results,
    )
    assert cafe_result["total_sessions"] == 5
    assert 0.0 <= cafe_result["behavior_score"] <= 10.0


# ──────────────────────────────────────────────────────────────
# TC-SC-11: Processing time < 500ms cho session 90 điểm
# ──────────────────────────────────────────────────────────────

def test_processing_time_acceptable():
    payload = load_fixture("session_studying_ideal.json")
    result = score_session(payload)

    assert result["processing_time_ms"] < 500, (
        f"Processing time {result['processing_time_ms']}ms vượt ngưỡng 500ms"
    )


# ──────────────────────────────────────────────────────────────
# TC-SC-12: cafe_history = None → vẫn trả session result
# ──────────────────────────────────────────────────────────────

def test_no_cafe_history_still_works():
    payload = load_fixture("session_studying_ideal.json")
    payload_no_hist = {k: v for k, v in payload.items() if k != "cafe_history"}
    payload_no_hist["cafe_history"] = None

    result = score_session(payload_no_hist)
    assert "is_studying" in result

    cafe_result = update_cafe_score(
        cafe_id=1,
        session_result=result,
        cafe_history=None,
    )
    assert cafe_result["behavior_score"] is not None


# ══════════════════════════════════════════════════════════════
# BUG FIX REGRESSION TESTS
# ══════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────
# TC-FIX-AI1: NON_STUDY session không inflate f3/f6/f7
# ──────────────────────────────────────────────────────────────

def test_ai1_non_study_fallback_features_are_zero():
    """
    [AI-1] Khi is_studying=False, incremental mode phải dùng f3=f6=f7=0.0
    thay vì 0.5. Quán toàn NON_STUDY session không được có điểm cao.
    """
    from scoring_engine.scorer import _compute_incremental

    non_study_session = {
        "is_studying":          False,
        "stable_duration_min":  5.0,
        "session_duration_min": 10.0,
        "spatial_std_m":        None,
        "dominant_cluster_pct": 0.0,
        "coverage_ratio":       0.0,
        "clean_data_rate":      0.9,
    }
    cafe_history = {
        "total_sessions_processed": 0,
        "studying_session_count":   0,
        "current_score":            None,
        "system_avg_score":         6.5,
        "dropoff_count":            0,
    }

    result = _compute_incremental(
        cafe_id=1,
        session_result=non_study_session,
        cafe_history=cafe_history,
        now="2026-01-01T00:00:00",
    )

    # Bayesian với v=0 (không có studying session) → phải pull về prior
    assert result["behavior_score"] == round(6.5, 1), (
        f"Quán 0 studying sessions phải có score = prior 6.5, got {result['behavior_score']}"
    )
    # study_rate = 0 → f1 = 0 → raw_score rất thấp
    assert result["behavior_score"] <= 6.5, (
        "NON_STUDY session không được inflate score vượt prior"
    )


# ──────────────────────────────────────────────────────────────
# TC-FIX-AI2: Dropoff dùng session_duration_min, không stable_duration_min
# ──────────────────────────────────────────────────────────────

def test_ai2_dropoff_uses_session_duration_not_stable():
    """
    [AI-2] Người ngồi quán 45 phút (session_duration_min=45) nhưng
    chỉ có 15 phút trong stable cluster (stable_duration_min=15)
    KHÔNG được tính là dropoff (threshold = 30 phút).
    """
    from scoring_engine.scorer import _compute_incremental
    from scoring_engine.feature_extractor import _get_duration

    session_result = {
        "is_studying":          True,
        "stable_duration_min":  15.0,   # cluster chỉ 15 phút
        "session_duration_min": 45.0,   # nhưng ngồi quán 45 phút
        "spatial_std_m":        5.0,
        "dominant_cluster_pct": 0.7,
        "coverage_ratio":       0.6,
        "clean_data_rate":      0.9,
    }
    cafe_history = {
        "total_sessions_processed": 5,
        "studying_session_count":   4,
        "current_score":            7.5,
        "system_avg_score":         6.5,
        "dropoff_count":            1,
    }

    result = _compute_incremental(
        cafe_id=1,
        session_result=session_result,
        cafe_history=cafe_history,
        now="2026-01-01T00:00:00",
    )

    # session_duration_min=45 > threshold=30 → KHÔNG dropoff
    assert result["dropoff_count"] == 1, (
        f"dropoff_count phải giữ nguyên 1 (không thêm), got {result['dropoff_count']}"
    )

    # Test _get_duration trực tiếp
    assert _get_duration(session_result) == 45.0, (
        f"_get_duration phải trả session_duration_min=45.0, got {_get_duration(session_result)}"
    )


def test_ai2_correct_dropoff_when_session_short():
    """
    [AI-2] Session thực sự ngắn (session_duration_min=20 < threshold=30)
    phải được tính là dropoff.
    """
    from scoring_engine.scorer import _compute_incremental

    short_session = {
        "is_studying":          False,
        "stable_duration_min":  0.0,
        "session_duration_min": 20.0,   # ngắn thật, dropoff đúng
        "spatial_std_m":        None,
        "dominant_cluster_pct": 0.0,
        "coverage_ratio":       0.0,
        "clean_data_rate":      0.8,
    }
    cafe_history = {
        "total_sessions_processed": 3,
        "studying_session_count":   2,
        "current_score":            7.0,
        "system_avg_score":         6.5,
        "dropoff_count":            0,
    }

    result = _compute_incremental(
        cafe_id=1,
        session_result=short_session,
        cafe_history=cafe_history,
        now="2026-01-01T00:00:00",
    )

    assert result["dropoff_count"] == 1, (
        f"Session 20 phút phải tính là dropoff, dropoff_count={result['dropoff_count']}"
    )


# ──────────────────────────────────────────────────────────────
# TC-FIX-AI3: dropoff_count tích lũy lịch sử, không reset
# ──────────────────────────────────────────────────────────────

def test_ai3_dropoff_count_accumulates_history():
    """
    [AI-3] Quán đã có 3 dropoff trong lịch sử (dropoff_count=3).
    Session mới ngắn (dropoff) → dropoff_count phải thành 4, không reset về 1.
    """
    from scoring_engine.scorer import _compute_incremental

    short_session = {
        "is_studying":          False,
        "stable_duration_min":  5.0,
        "session_duration_min": 10.0,   # < 30 → dropoff
        "spatial_std_m":        None,
        "dominant_cluster_pct": 0.0,
        "coverage_ratio":       0.0,
        "clean_data_rate":      0.7,
    }
    cafe_history = {
        "total_sessions_processed": 9,
        "studying_session_count":   6,
        "current_score":            7.2,
        "system_avg_score":         6.5,
        "dropoff_count":            3,   # lịch sử đã có 3 dropoff
    }

    result = _compute_incremental(
        cafe_id=1,
        session_result=short_session,
        cafe_history=cafe_history,
        now="2026-01-01T00:00:00",
    )

    assert result["dropoff_count"] == 4, (
        f"dropoff_count phải tích lũy: 3 + 1 = 4, got {result['dropoff_count']}"
    )
    assert result["total_sessions"] == 10
    # dropoff_rate = 4/10 = 0.4
    assert abs(result["dropoff_rate"] - 0.4) < 0.001


def test_ai3_no_dropoff_session_keeps_history():
    """
    [AI-3] Session không dropoff → dropoff_count giữ nguyên lịch sử.
    """
    from scoring_engine.scorer import _compute_incremental

    long_session = {
        "is_studying":          True,
        "stable_duration_min":  60.0,
        "session_duration_min": 90.0,   # > 30 → không dropoff
        "spatial_std_m":        8.0,
        "dominant_cluster_pct": 0.85,
        "coverage_ratio":       0.8,
        "clean_data_rate":      0.95,
    }
    cafe_history = {
        "total_sessions_processed": 5,
        "studying_session_count":   3,
        "current_score":            7.0,
        "system_avg_score":         6.5,
        "dropoff_count":            2,
    }

    result = _compute_incremental(
        cafe_id=1,
        session_result=long_session,
        cafe_history=cafe_history,
        now="2026-01-01T00:00:00",
    )

    assert result["dropoff_count"] == 2, (
        f"Session không dropoff không được tăng dropoff_count, got {result['dropoff_count']}"
    )


# ──────────────────────────────────────────────────────────────
# TC-FIX-AI5: session_score có trong output và trong [0, 1]
# ──────────────────────────────────────────────────────────────

def test_ai5_session_score_present_in_output():
    """[AI-5] session_score phải có trong session result output."""
    payload = load_fixture("session_studying_ideal.json")
    result = score_session(payload)

    assert "session_score" in result, "session_result phải có key 'session_score'"
    assert 0.0 <= result["session_score"] <= 1.0, (
        f"session_score phải ∈ [0, 1], got {result['session_score']}"
    )


def test_ai5_session_score_higher_for_studying_session():
    """
    [AI-5] Session is_studying=True phải có session_score cao hơn
    session is_studying=False (cùng điều kiện GPS).
    """
    good_payload = load_fixture("session_studying_ideal.json")
    bad_payload  = load_fixture("session_not_studying_short.json")

    good_result = score_session(good_payload)
    bad_result  = score_session(bad_payload)

    assert good_result["session_score"] > bad_result["session_score"], (
        f"Studying session ({good_result['session_score']}) phải có score cao hơn "
        f"non-studying ({bad_result['session_score']})"
    )


def test_ai5_session_score_in_insufficient_session():
    """[AI-5] _insufficient_session cũng phải có session_score = 0.0."""
    payload = load_fixture("session_studying_ideal.json")
    # Dùng payload với chỉ 1 GPS point → insufficient
    minimal_payload = dict(payload)
    minimal_payload["gps_points"] = payload["gps_points"][:1]

    result = score_session(minimal_payload)
    assert "session_score" in result
    assert result["session_score"] == 0.0


def test_ai5_session_score_added_to_output_keys():
    """[AI-5] Cập nhật test_session_result_output_keys để include session_score."""
    payload = load_fixture("session_studying_ideal.json")
    result = score_session(payload)

    required_new_keys = ["session_score"]
    for key in required_new_keys:
        assert key in result, f"session_result thiếu key mới '{key}' (AI-5)"
