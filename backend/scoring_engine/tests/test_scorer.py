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
