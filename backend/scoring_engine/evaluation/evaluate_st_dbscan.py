"""
evaluate_st_dbscan.py — Synthetic Evaluation cho module ST-DBSCAN.

Mục đích:
    Đo Accuracy, Precision, Recall, F1 của bước phân loại is_studying
    bằng cách tạo tập dataset synthetic có nhãn tính từ công thức toán học.

Tại sao synthetic thay vì GPS thật?
    - Không cần thu thập dữ liệu thực địa (tốn thời gian).
    - Nhãn 100% chính xác vì tính từ công thức, không phụ thuộc AI.
    - Có thể kiểm soát phân phối dataset: bao nhiêu % studying, bao nhiêu % không.

Giới hạn:
    - Không phản ánh GPS drift/noise thực tế từ điện thoại.
    - Hyperparameter đúng về mặt toán học chưa chắc đúng với GPS thật.
    - Field test vẫn là bước cần thiết sau script này.

Chạy:
    cd backend/
    python scoring_engine/evaluate_st_dbscan.py

    # Tùy chọn:
    python scoring_engine/evaluate_st_dbscan.py --n-sessions 200 --export-csv
    python scoring_engine/evaluate_st_dbscan.py --noise-gps --verbose
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scoring_engine import config
from scoring_engine.noise_filter import apply_noise_filter, get_clean_points
from scoring_engine.st_dbscan import run_st_dbscan
from scoring_engine.utils.validators import validate_and_parse_gps_points

# ── Constants ─────────────────────────────────────────────────────────────────
CAFE_LAT = 21.0024
CAFE_LNG = 105.8453
CAFE_RADIUS = 50.0

_LAT_PER_M = 1.0 / 111_320.0
_LNG_PER_M = 1.0 / (111_320.0 * math.cos(math.radians(CAFE_LAT)))
BASE_TIME = datetime(2026, 4, 10, 8, 0, 0, tzinfo=timezone.utc)

# RNG seed cố định → reproducible
_RNG = random.Random(2024)


# =============================================================================
# Dataclass mô tả một session trong dataset
# =============================================================================

@dataclass
class SessionSpec:
    """
    Mô tả một session trong synthetic dataset.
    true_label được tính từ công thức — không do AI gán.
    """
    session_id:   str
    profile:      str          # tên profile để group trong report
    true_label:   bool         # is_studying ground truth (tính từ công thức)
    label_reason: str          # lý do gán nhãn (để audit)
    gps_points:   List[dict]   # list {lat, lng, accuracy, timestamp (str ISO)}


# =============================================================================
# Profile generators — mỗi profile là một tình huống GPS cụ thể
# =============================================================================
#
# Mỗi profile có docstring giải thích:
#   - Mô tả tình huống
#   - Tại sao true_label = True/False (công thức nào quyết định)
#   - Điều kiện ST-DBSCAN nào bị fail (nếu False)
#

def _pts(
    n: int,
    offset_m: float = 0.0,
    start_min: float = 0.0,
    interval_min: float = 1.0,
    spread_m: float = 5.0,
    accuracy: float = 12.0,
    noise_accuracy_pct: float = 0.0,   # % điểm có accuracy > 50m
) -> List[dict]:
    """
    Helper sinh GPS points. Dùng jitter pattern cố định để spatial_std
    tính được từ công thức, không phụ thuộc random.

    noise_accuracy_pct: tỷ lệ điểm bị inject accuracy > 50m (mô phỏng GPS nhiễu).
    """
    pts = []
    for i in range(n):
        j_lat = (i % 3 - 1) * (spread_m / 3.0)
        j_lng = (i % 2) * (spread_m / 4.0)
        ts = BASE_TIME + timedelta(minutes=start_min + i * interval_min)

        # Inject noisy accuracy nếu được yêu cầu
        if noise_accuracy_pct > 0 and _RNG.random() < noise_accuracy_pct:
            acc = _RNG.uniform(60.0, 150.0)   # accuracy tồi — sẽ bị noise filter lớp A
        else:
            acc = accuracy + _RNG.uniform(-2.0, 2.0)

        pts.append({
            "lat":       CAFE_LAT + (offset_m + j_lat) * _LAT_PER_M,
            "lng":       CAFE_LNG + j_lng * _LNG_PER_M,
            "accuracy":  round(acc, 1),
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    return pts


def _make_session(sid: str, profile: str, true_label: bool,
                  label_reason: str, pts: List[dict]) -> SessionSpec:
    return SessionSpec(
        session_id=sid, profile=profile,
        true_label=true_label, label_reason=label_reason,
        gps_points=pts,
    )


# ── TRUE profiles (is_studying = True) ───────────────────────────────────────

def profile_ideal_study(idx: int) -> SessionSpec:
    """
    Học lý tưởng: 90 điểm, 90 phút, spread 5m, accuracy tốt.
    true_label=True vì:
        n=90 >= MIN_CLEAN_POINTS=5 ✓
        span=89min >= MIN_STABLE_DURATION_MIN=20 ✓
        dominant_pct=1.0 >= DOMINANT_CLUSTER_PCT=0.60 ✓
        centroid=offset 0m << effective_radius=70m ✓
        spatial_std ≈ 3m << MAX_SPATIAL_STD_M=30m ✓
    """
    n = _RNG.randint(60, 120)
    pts = _pts(n, offset_m=0.0, interval_min=1.0, spread_m=5.0)
    return _make_session(
        f"ideal_{idx}", "ideal_study", True,
        f"n={n}≥5, span={(n-1):.0f}min≥20, offset=0m<70m, pct=1.0≥0.60", pts
    )


def profile_long_study(idx: int) -> SessionSpec:
    """
    Học dài: 180 phút, spread 7m (drift lớn hơn chút).
    true_label=True — tất cả điều kiện thỏa.
    """
    n = _RNG.randint(150, 200)
    pts = _pts(n, offset_m=_RNG.uniform(0, 10), interval_min=1.0, spread_m=7.0)
    return _make_session(
        f"long_{idx}", "long_study", True,
        f"n={n}≥5, span={(n-1):.0f}min≥20, drift≤7m<30m", pts
    )


def profile_near_boundary_duration(idx: int) -> SessionSpec:
    """
    Học vừa đủ ngưỡng thời gian: span ∈ [21, 25] phút.
    true_label=True — đúng ngưỡng.
    """
    n = _RNG.randint(22, 26)
    pts = _pts(n, offset_m=0.0, interval_min=1.0, spread_m=4.0)
    span = n - 1
    return _make_session(
        f"boundary_dur_{idx}", "boundary_duration", True,
        f"span={span}min — vừa trên ngưỡng MIN_STABLE_DURATION_MIN=20", pts
    )


def profile_near_boundary_radius(idx: int) -> SessionSpec:
    """
    Ngồi gần rìa quán: centroid ∈ [55, 68] m từ tâm.
    true_label=True — trong effective_radius = 50 + 20 = 70m.
    """
    offset = _RNG.uniform(55.0, 68.0)
    pts = _pts(60, offset_m=offset, interval_min=1.0, spread_m=4.0)
    return _make_session(
        f"boundary_rad_{idx}", "boundary_radius", True,
        f"centroid≈{offset:.0f}m < effective_radius=70m", pts
    )


def profile_near_boundary_purity(idx: int) -> SessionSpec:
    """
    Dominant cluster chiếm 62–70% (vừa trên ngưỡng 60%).
    Thêm một số điểm rải rác để purity không phải 100%.
    true_label=True — dominant_pct >= 0.60.
    """
    n_cluster = _RNG.randint(38, 45)
    n_scatter = int(n_cluster * _RNG.uniform(0.40, 0.50))  # 40–50% điểm rải rác
    total = n_cluster + n_scatter

    cluster = _pts(n_cluster, offset_m=0.0, start_min=0.0,
                   interval_min=1.0, spread_m=4.0)
    scatter = [
        {
            "lat":       CAFE_LAT + _RNG.uniform(30, 45) * _LAT_PER_M,
            "lng":       CAFE_LNG + _RNG.uniform(30, 45) * _LNG_PER_M,
            "accuracy":  12.0,
            "timestamp": (BASE_TIME + timedelta(minutes=0.5 + i * 0.8)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        }
        for i in range(n_scatter)
    ]
    pts = sorted(cluster + scatter, key=lambda p: p["timestamp"])
    pct_approx = n_cluster / total
    return _make_session(
        f"boundary_purity_{idx}", "boundary_purity", True,
        f"dominant≈{pct_approx:.2f}≥0.60, total={total}", pts
    )


def profile_with_gps_noise(idx: int) -> SessionSpec:
    """
    Session học tốt nhưng 20% điểm GPS có accuracy > 50m.
    true_label=True — noise filter lớp A lọc điểm tệ,
    phần còn lại đủ để ST-DBSCAN phân loại đúng.
    """
    n = _RNG.randint(80, 100)
    pts = _pts(n, offset_m=0.0, interval_min=1.0, spread_m=5.0,
               noise_accuracy_pct=0.20)
    return _make_session(
        f"noisy_{idx}", "study_with_noise", True,
        f"n={n}, 20% điểm accuracy>50m — noise filter lọc, còn lại đủ điều kiện", pts
    )


def profile_two_sessions_same_spot(idx: int) -> SessionSpec:
    """
    Ngồi 2 lần cùng chỗ: 8h–9h30 (90 điểm) và 14h–14h20 (20 điểm).
    Lần 1 dài hơn nhiều → dominant_pct = 90/110 = 0.818 ≥ 0.60.
    ST-DBSCAN tách 2 cluster vì eps_temporal=600s — dominant cluster = lần học sáng.

    FIX: Không dùng 2 session BẰNG NHAU (50/50 → dominant_pct=0.50 → False).
    Cần 1 session rõ ràng dài hơn để dominant_pct ≥ 0.60.

    true_label=True vì:
        dominant_cluster = session sáng (90 điểm = 81.8%)
        dominant_pct = 0.818 ≥ DOMINANT_CLUSTER_PCT=0.60 ✓
        stable_duration = 89 phút ≥ MIN_STABLE_DURATION_MIN=20 ✓
        centroid ≈ 0m từ tâm quán ✓
    """
    # Session sáng: 90 phút (dominant)
    session_a = _pts(90, offset_m=0.0, start_min=0.0, interval_min=1.0, spread_m=5.0)
    # Session chiều: 20 phút (minority — cùng chỗ nhưng ít điểm hơn)
    session_b = _pts(20, offset_m=0.0, start_min=360.0, interval_min=1.0, spread_m=5.0)
    pts = session_a + session_b
    dominant_pct = len(session_a) / len(pts)
    return _make_session(
        f"two_sessions_{idx}", "two_sessions_same_spot", True,
        f"dominant_pct={dominant_pct:.2f}≥0.60 (90pts sáng vs 20pts chiều), stable=89min", pts
    )


# ── FALSE profiles (is_studying = False) ─────────────────────────────────────

def profile_short_visit(idx: int) -> SessionSpec:
    """
    Ghé qua nhanh: span ∈ [5, 19] phút.
    true_label=False vì:
        span < MIN_STABLE_DURATION_MIN=20 phút → reason='too_short'
    """
    n = _RNG.randint(6, 20)
    pts = _pts(n, offset_m=0.0, interval_min=1.0, spread_m=3.0)
    span = n - 1
    return _make_session(
        f"short_{idx}", "short_visit", False,
        f"span={span}min < MIN_STABLE_DURATION_MIN=20 → too_short", pts
    )


def profile_outside_cafe(idx: int) -> SessionSpec:
    """
    Ngồi quán kế bên: centroid ∈ [80, 200] m từ tâm.
    true_label=False vì:
        centroid > effective_radius=70m → reason='outside_cafe_radius'
    """
    offset = _RNG.uniform(80.0, 200.0)
    pts = _pts(60, offset_m=offset, interval_min=1.0, spread_m=5.0)
    return _make_session(
        f"outside_{idx}", "outside_cafe", False,
        f"centroid≈{offset:.0f}m > effective_radius=70m → outside_cafe_radius", pts
    )


def profile_continuous_movement(idx: int) -> SessionSpec:
    """
    Di chuyển liên tục: mỗi điểm cách điểm trước 30–50m.
    true_label=False vì:
        Không tạo được cluster nào → dominant_pct < 0.60
        → reason='low_cluster_purity' hoặc 'no_cluster'
    """
    n = 60
    pts = []
    lat, lng = CAFE_LAT, CAFE_LNG
    for i in range(n):
        step_m = _RNG.uniform(30, 50)
        direction = _RNG.uniform(0, 2 * math.pi)
        lat += step_m * math.cos(direction) * _LAT_PER_M
        lng += step_m * math.sin(direction) * _LNG_PER_M
        ts = BASE_TIME + timedelta(minutes=i * 1.0)
        pts.append({
            "lat": lat, "lng": lng,
            "accuracy": 12.0,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    return _make_session(
        f"move_{idx}", "continuous_movement", False,
        "di chuyển 30–50m/phút → không cluster ổn định → low_cluster_purity", pts
    )


def profile_insufficient_points(idx: int) -> SessionSpec:
    """
    Quá ít điểm GPS: n ∈ [1, 4].
    true_label=False vì:
        n < MIN_CLEAN_POINTS=5 → reason='too_short'
    """
    n = _RNG.randint(1, 4)
    pts = _pts(n, offset_m=0.0, interval_min=10.0, spread_m=3.0)
    return _make_session(
        f"few_pts_{idx}", "insufficient_points", False,
        f"n={n} < MIN_CLEAN_POINTS=5 → too_short", pts
    )


def profile_all_noisy_gps(idx: int) -> SessionSpec:
    """
    GPS rất tệ: 92% điểm accuracy > 50m → sau filter chỉ còn 2–3 điểm sạch.
    true_label=False vì:
        Sau noise filter còn < MIN_CLEAN_POINTS=5 điểm sạch → too_short.

    FIX: Dùng noise_pct=0.92 thay vì 0.80 để đảm bảo
         n_clean < 5 với mọi random seed (tránh edge case FP).
    Với n=30, noise_pct=0.92: expected clean ≈ 30 × 0.08 = 2.4 < 5 ✓
    """
    n = 30
    pts = _pts(n, offset_m=0.0, interval_min=2.0, spread_m=5.0,
               noise_accuracy_pct=0.92)
    return _make_session(
        f"all_noisy_{idx}", "all_noisy_gps", False,
        "92% accuracy>50m → noise filter → <5 điểm sạch → too_short"
    , pts)


def profile_split_location(idx: int) -> SessionSpec:
    """
    Thời gian đủ nhưng 2 vị trí đều nhau (50/50).
    true_label=False vì:
        dominant_pct = 0.50 < DOMINANT_CLUSTER_PCT=0.60
        → reason='low_cluster_purity'
    """
    n_each = _RNG.randint(25, 35)
    loc_a = _pts(n_each, offset_m=0.0, start_min=0.0,
                 interval_min=2.0, spread_m=3.0)
    loc_b = _pts(n_each, offset_m=30.0, start_min=1.0,
                 interval_min=2.0, spread_m=3.0)
    pts = sorted(loc_a + loc_b, key=lambda p: p["timestamp"])
    return _make_session(
        f"split_{idx}", "split_location", False,
        f"2 cluster {n_each}/{n_each} (50/50) → dominant_pct=0.50<0.60 → low_cluster_purity", pts
    )


# =============================================================================
# Dataset builder
# =============================================================================

# Phân phối: (profile_function, tỷ lệ trong dataset)
# TRUE_PROFILES:  60% tổng dataset
# FALSE_PROFILES: 40% tổng dataset
TRUE_PROFILES = [
    (profile_ideal_study,             0.30),  # 30% — trường hợp phổ biến nhất
    (profile_long_study,              0.10),  # 10%
    (profile_near_boundary_duration,  0.08),  # 8%  — test boundary
    (profile_near_boundary_radius,    0.05),  # 5%  — test boundary
    (profile_near_boundary_purity,    0.05),  # 5%  — test boundary
    (profile_with_gps_noise,          0.07),  # 7%  — realistic noise
    (profile_two_sessions_same_spot,  0.05),  # 5%  — ST-DBSCAN advantage
]

FALSE_PROFILES = [
    (profile_short_visit,             0.15),  # 15%
    (profile_outside_cafe,            0.10),  # 10%
    (profile_continuous_movement,     0.07),  # 7%
    (profile_insufficient_points,     0.05),  # 5%
    (profile_all_noisy_gps,           0.05),  # 5%
    (profile_split_location,          0.08),  # 8%
]


def build_dataset(n_total: int) -> List[SessionSpec]:
    """
    Tạo dataset synthetic với phân phối đã định nghĩa.
    n_total: tổng số sessions muốn tạo.
    """
    sessions = []
    idx = 0

    for gen_fn, ratio in TRUE_PROFILES + FALSE_PROFILES:
        count = max(1, round(n_total * ratio))
        for _ in range(count):
            sessions.append(gen_fn(idx))
            idx += 1

    _RNG.shuffle(sessions)
    return sessions


# =============================================================================
# Evaluation engine
# =============================================================================

def _run_pipeline(session: SessionSpec) -> dict:
    """
    Chạy noise_filter → st_dbscan cho một session.
    Trả về dict kết quả của run_st_dbscan.
    """
    # Parse GPS points (validators handle timestamp parsing)
    parsed = validate_and_parse_gps_points(session.gps_points)

    # Noise filter
    annotated, _ = apply_noise_filter(
        parsed,
        cafe_center_lat=CAFE_LAT,
        cafe_center_lng=CAFE_LNG,
        cafe_radius_m=CAFE_RADIUS,
    )
    clean = get_clean_points(annotated)

    # ST-DBSCAN
    return run_st_dbscan(clean, CAFE_LAT, CAFE_LNG, CAFE_RADIUS)


def evaluate(sessions: List[SessionSpec], verbose: bool = False) -> dict:
    """
    Chạy pipeline cho toàn bộ dataset, tính confusion matrix và metrics.
    """
    records = []
    start_time = time.perf_counter()

    for session in sessions:
        t0 = time.perf_counter()
        result = _run_pipeline(session)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        pred = bool(result.get("is_studying", False))
        true = session.true_label
        correct = (pred == true)

        records.append({
            "session_id":      session.session_id,
            "profile":         session.profile,
            "true_label":      true,
            "pred_label":      pred,
            "correct":         correct,
            "reason":          result.get("reason"),
            "stable_dur_min":  result.get("stable_duration_min", 0.0),
            "dominant_pct":    result.get("dominant_cluster_pct", 0.0),
            "spatial_std_m":   result.get("spatial_std_m"),
            "label_reason":    session.label_reason,
            "elapsed_ms":      round(elapsed_ms, 2),
        })

        if verbose and not correct:
            print(f"  [WRONG] {session.session_id} | true={true} pred={pred}"
                  f" | reason={result.get('reason')} | {session.label_reason}")

    total_time = (time.perf_counter() - start_time) * 1000

    # ── Confusion matrix ────────────────────────────────────────────────────
    TP = sum(1 for r in records if r["true_label"] and r["pred_label"])
    FP = sum(1 for r in records if not r["true_label"] and r["pred_label"])
    FN = sum(1 for r in records if r["true_label"] and not r["pred_label"])
    TN = sum(1 for r in records if not r["true_label"] and not r["pred_label"])

    total   = len(records)
    correct = TP + TN

    precision = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    recall    = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)
    accuracy  = correct / total if total > 0 else 0.0

    # ── Per-profile breakdown ────────────────────────────────────────────────
    profile_stats = {}
    for r in records:
        p = r["profile"]
        if p not in profile_stats:
            profile_stats[p] = {"total": 0, "correct": 0, "true_label": r["true_label"]}
        profile_stats[p]["total"] += 1
        if r["correct"]:
            profile_stats[p]["correct"] += 1

    return {
        "total":         total,
        "correct":       correct,
        "TP": TP, "FP": FP, "FN": FN, "TN": TN,
        "accuracy":      accuracy,
        "precision":     precision,
        "recall":        recall,
        "f1":            f1,
        "total_time_ms": round(total_time, 1),
        "avg_time_ms":   round(total_time / total, 2) if total > 0 else 0,
        "profile_stats": profile_stats,
        "records":       records,
    }


# =============================================================================
# Report printer
# =============================================================================

def print_report(result: dict) -> None:
    """In báo cáo kết quả ra stdout."""

    W = 60  # độ rộng console

    print("\n" + "=" * W)
    print("  SYNTHETIC EVALUATION — ST-DBSCAN (is_studying)")
    print("  StudyCafe Analytics System — Scoring Engine v2.0.0")
    print("=" * W)

    # ── Confusion matrix ────────────────────────────────────────────────────
    print("\n[ Confusion Matrix ]")
    print(f"  {'':25s} {'Pred TRUE':>12} {'Pred FALSE':>12}")
    print(f"  {'Actual TRUE':25s} {'TP=' + str(result['TP']):>12} {'FN=' + str(result['FN']):>12}")
    print(f"  {'Actual FALSE':25s} {'FP=' + str(result['FP']):>12} {'TN=' + str(result['TN']):>12}")

    # ── Core metrics ─────────────────────────────────────────────────────────
    print("\n[ Metrics ]")
    items = [
        ("Accuracy",  result["accuracy"],  "✓ >0.85 mục tiêu" if result["accuracy"] >= 0.85 else "✗ <0.85"),
        ("Precision", result["precision"], "✓ >0.80 mục tiêu" if result["precision"] >= 0.80 else "✗ <0.80"),
        ("Recall",    result["recall"],    "✓ >0.80 mục tiêu" if result["recall"] >= 0.80 else "✗ <0.80"),
        ("F1 Score",  result["f1"],        "✓ >0.80 mục tiêu" if result["f1"] >= 0.80 else "✗ <0.80"),
    ]
    for name, val, note in items:
        bar_len = int(val * 30)
        bar = "█" * bar_len + "░" * (30 - bar_len)
        print(f"  {name:12s} {val:.4f}  [{bar}]  {note}")

    print(f"\n  Tổng sessions : {result['total']}")
    print(f"  Đúng / Sai    : {result['correct']} / {result['total'] - result['correct']}")
    print(f"  Thời gian     : {result['total_time_ms']:.0f}ms tổng"
          f" ({result['avg_time_ms']:.1f}ms/session)")

    # ── Per-profile breakdown ─────────────────────────────────────────────────
    print("\n[ Kết quả theo Profile ]")
    print(f"  {'Profile':30s} {'Label':6} {'Đúng':6} {'Tổng':6} {'Acc':>6}")
    print("  " + "-" * 54)
    for profile, stats in sorted(result["profile_stats"].items()):
        lbl = "TRUE " if stats["true_label"] else "FALSE"
        acc = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
        bar = "●" * stats["correct"] + "○" * (stats["total"] - stats["correct"])
        print(f"  {profile:30s} {lbl}  {stats['correct']:>4}/{stats['total']:<4}  "
              f"{acc:.0%}  {bar}")

    # ── Nhận xét ─────────────────────────────────────────────────────────────
    print("\n[ Nhận xét ]")

    fn_records = [r for r in result["records"] if r["true_label"] and not r["pred_label"]]
    fp_records = [r for r in result["records"] if not r["true_label"] and r["pred_label"]]

    if fn_records:
        print(f"  FALSE NEGATIVE ({len(fn_records)} sessions) — học thật bị bỏ sót:")
        for r in fn_records[:5]:
            print(f"    - {r['session_id']:20s} reason={r['reason']:25s}"
                  f" stable={r['stable_dur_min']:.1f}min")
    else:
        print("  FALSE NEGATIVE: 0 — không bỏ sót session học thật.")

    if fp_records:
        print(f"  FALSE POSITIVE ({len(fp_records)} sessions) — không học bị nhận nhầm:")
        for r in fp_records[:5]:
            print(f"    - {r['session_id']:20s} dominant_pct={r['dominant_pct']:.2f}"
                  f" stable={r['stable_dur_min']:.1f}min")
    else:
        print("  FALSE POSITIVE: 0 — không nhận nhầm session không học.")

    # ── Đánh giá tổng thể ────────────────────────────────────────────────────
    print("\n[ Đánh giá tổng thể ]")
    if result["f1"] >= 0.90:
        verdict = "EXCELLENT — Pipeline hoạt động xuất sắc trên synthetic data."
    elif result["f1"] >= 0.80:
        verdict = "GOOD — Đạt acceptance criteria (F1 ≥ 0.80)."
    elif result["f1"] >= 0.70:
        verdict = "FAIR — Cần xem xét điều chỉnh hyperparameter."
    else:
        verdict = "POOR — Pipeline cần review lại logic hoặc hyperparameter."

    print(f"  {verdict}")
    print(f"\n  LƯU Ý: Kết quả này đo logic toán học, không phải GPS thật.")
    print(f"  Cần field test để validate trên GPS điện thoại thực tế.")
    print("=" * W + "\n")


def export_csv(result: dict, path: str) -> None:
    """Xuất toàn bộ records ra CSV để phân tích thêm."""
    fields = [
        "session_id", "profile", "true_label", "pred_label", "correct",
        "reason", "stable_dur_min", "dominant_pct", "spatial_std_m",
        "label_reason", "elapsed_ms",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result["records"])
    print(f"  CSV exported → {path}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Synthetic evaluation cho ST-DBSCAN module"
    )
    parser.add_argument(
        "--n-sessions", type=int, default=150,
        help="Tổng số sessions trong dataset (default: 150)"
    )
    parser.add_argument(
        "--export-csv", action="store_true",
        help="Xuất kết quả ra CSV"
    )
    parser.add_argument(
        "--csv-path", type=str, default="st_dbscan_eval_results.csv",
        help="Đường dẫn file CSV output (default: st_dbscan_eval_results.csv)"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="In chi tiết các session dự đoán sai"
    )
    args = parser.parse_args()

    print(f"\nBuilding synthetic dataset ({args.n_sessions} sessions)...")
    sessions = build_dataset(args.n_sessions)

    n_true  = sum(1 for s in sessions if s.true_label)
    n_false = sum(1 for s in sessions if not s.true_label)
    print(f"  TRUE  (is_studying=True) : {n_true} sessions")
    print(f"  FALSE (is_studying=False): {n_false} sessions")
    print(f"  Profiles: {len(set(s.profile for s in sessions))} loại")

    print(f"\nRunning evaluation...")
    result = evaluate(sessions, verbose=args.verbose)

    print_report(result)

    if args.export_csv:
        export_csv(result, args.csv_path)


if __name__ == "__main__":
    main()
