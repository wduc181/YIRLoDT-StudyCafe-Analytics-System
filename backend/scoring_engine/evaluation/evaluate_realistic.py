"""
evaluate_realistic.py — Realistic Evaluation cho ST-DBSCAN.

Tổng quan:
    
    Script này: label được gán theo HÀNH VI THỰC TẾ của người dùng.
    GPS được sinh với noise thực tế (Brownian drift, GPS jump, accuracy
    borderline). Pipeline KHÔNG biết trước label — có những case pipeline
    sẽ sai vì đó là giới hạn thật của thuật toán.

PHÂN LOẠI LABEL:
    TRUE  = Người thực sự có hành vi học tập (ngồi yên trong quán)
    FALSE = Người không học (đứng chờ, ghé qua, ngủ, đi lại ngoài quán)

    Pipeline KHÔNG THỂ phân biệt: ngủ vs học, nhắn tin vs học,...
    → Đây là fundamental limitation được ghi nhận trong report.

Chạy:
    cd backend/
    python scoring_engine/evaluate_realistic.py
    python scoring_engine/evaluate_realistic.py --n 300 --seed 42 --csv
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
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scoring_engine import config
from scoring_engine.noise_filter import apply_noise_filter, get_clean_points
from scoring_engine.st_dbscan import run_st_dbscan
from scoring_engine.utils.validators import validate_and_parse_gps_points

# ── Cafe reference ─────────────────────────────────────────────────────────────
CAFE_LAT    = 21.0024
CAFE_LNG    = 105.8453
CAFE_RADIUS = 50.0

_LPM = 1.0 / 111_320.0                                    # degree per metre (lat)
_LGM = 1.0 / (111_320.0 * math.cos(math.radians(CAFE_LAT)))  # degree per metre (lng)
T0   = datetime(2026, 4, 10, 8, 0, 0, tzinfo=timezone.utc)


# =============================================================================
# Data class
# =============================================================================

@dataclass
class Session:
    sid:          str
    profile:      str
    true_label:   bool          # ground truth — hành vi thực tế
    ambiguous:    bool          # True = pipeline không thể phân biệt được về nguyên tắc
    note:         str           # giải thích tại sao label = True/False
    gps_points:   List[dict]


# =============================================================================
# GPS noise helpers — mô phỏng GPS thực tế
# =============================================================================

def _pt(lat, lng, t_min: float, rng: random.Random,
        accuracy_range=(10, 20)) -> dict:
    return {
        "lat":       lat,
        "lng":       lng,
        "accuracy":  round(rng.uniform(*accuracy_range), 1),
        "timestamp": (T0 + timedelta(minutes=t_min)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _study_gps(n: int, center_offset_m: float, rng: random.Random,
               brownian_std_m: float = 5.0,
               jump_prob: float = 0.05, jump_range_m=(5, 20),
               accuracy_spike_prob: float = 0.08,
               accuracy_spike_range=(55, 120),
               base_accuracy=(10, 22),
               interval_min: float = 1.0,
               start_min: float = 0.0) -> List[dict]:
    """
    Sinh GPS điểm mô phỏng người ĐANG HỌC thực tế:
    - Brownian drift: GPS trôi nhẹ dù ngồi yên (indoor multipath)
    - Occasional jump: 5% điểm nhảy 5-20m rồi về (GPS glitch)
    - Accuracy spike: 8% điểm có accuracy > 50m (tín hiệu yếu bất thường)
    """
    pts = []
    base_lat = CAFE_LAT + center_offset_m * _LPM
    base_lng = CAFE_LNG

    for i in range(n):
        # Brownian drift — GPS thực tế trôi từ từ
        d_lat = rng.gauss(0, brownian_std_m) * _LPM
        d_lng = rng.gauss(0, brownian_std_m) * _LGM

        # GPS jump ngẫu nhiên
        if rng.random() < jump_prob:
            jmp   = rng.uniform(*jump_range_m)
            ang   = rng.uniform(0, 2 * math.pi)
            d_lat += jmp * math.cos(ang) * _LPM
            d_lng += jmp * math.sin(ang) * _LGM

        # Accuracy spike
        if rng.random() < accuracy_spike_prob:
            acc_r = accuracy_spike_range
        else:
            acc_r = base_accuracy

        pts.append(_pt(base_lat + d_lat, base_lng + d_lng,
                       start_min + i * interval_min, rng, acc_r))
    return pts


def _outside_gps(n: int, offset_m: float, rng: random.Random,
                 spread_m: float = 4.0,
                 interval_min: float = 1.0) -> List[dict]:
    """Sinh GPS điểm cho người ở NGOÀI quán."""
    pts = []
    for i in range(n):
        ang  = rng.uniform(0, 2 * math.pi)
        plat = CAFE_LAT + offset_m * math.cos(ang) * _LPM + rng.gauss(0, spread_m) * _LPM
        plng = CAFE_LNG + offset_m * math.sin(ang) * _LGM + rng.gauss(0, spread_m) * _LGM
        pts.append(_pt(plat, plng, i * interval_min, rng))
    return pts


# =============================================================================
# Profile generators — mỗi profile là một tình huống thực tế
# Label được gán theo HÀNH VI người dùng, không phải công thức ngưỡng
# =============================================================================

# ──────────────────────────────────────────────
# TRUE profiles — người THỰC SỰ học
# ──────────────────────────────────────────────

def p_ideal_study(idx: int, rng: random.Random) -> Session:
    """Học điển hình 60-120 phút, GPS tốt với noise thực tế."""
    n = rng.randint(60, 120)
    pts = _study_gps(n, center_offset_m=rng.uniform(0, 10), rng=rng,
                     brownian_std_m=rng.uniform(3, 7))
    return Session(f"ideal_{idx}", "ideal_study", True, False,
                   f"Ngồi học {n} phút, brownian drift, GPS spike bình thường", pts)


def p_study_with_toilet_break(idx: int, rng: random.Random) -> Session:
    """
    Học 90 phút, ra ngoài đi vệ sinh 1 lần 5-9 phút.
    Label=True: nghỉ ngắn không phủ nhận việc học.
    """
    break_start = rng.randint(20, 60)
    break_dur   = rng.randint(5, 9)
    pts = []
    for i in range(90):
        if break_start <= i < break_start + break_dur:
            # Ra ngoài 30-80m
            off = rng.uniform(30, 80)
            ang = rng.uniform(0, 2 * math.pi)
            lat = CAFE_LAT + off * math.cos(ang) * _LPM + rng.gauss(0, 3) * _LPM
            lng = CAFE_LNG + off * math.sin(ang) * _LGM + rng.gauss(0, 3) * _LGM
            pts.append(_pt(lat, lng, float(i), rng))
        else:
            pts += _study_gps(1, center_offset_m=rng.uniform(0, 8), rng=rng,
                               brownian_std_m=4.0, start_min=float(i))
    return Session(f"toilet_{idx}", "study_toilet_break", True, False,
                   f"Học 90 phút, nghỉ vệ sinh {break_dur} phút tại phút {break_start}", pts)


def p_study_borderline_duration(idx: int, rng: random.Random) -> Session:
    """
    Học đúng 20-25 phút.
    Label=True: đủ thời gian theo định nghĩa hệ thống.
    """
    n = rng.randint(21, 26)
    pts = _study_gps(n, center_offset_m=rng.uniform(0, 8), rng=rng,
                     brownian_std_m=4.0)
    return Session(f"short_study_{idx}", "borderline_duration", True, False,
                   f"Học {n} phút — vừa trên ngưỡng 20 phút", pts)


def p_study_near_window(idx: int, rng: random.Random) -> Session:
    """
    Ngồi gần cửa sổ quán — GPS nhận outdoor signal tốt hơn nhưng drift nhiều.
    centroid 40-65m từ tâm quán — trong buffer zone.
    Label=True: vẫn trong quán, đang học.
    """
    offset = rng.uniform(40, 65)
    pts = _study_gps(60, center_offset_m=offset, rng=rng,
                     brownian_std_m=rng.uniform(5, 10))
    return Session(f"window_{idx}", "study_near_window", True, False,
                   f"Ngồi cửa sổ, centroid≈{offset:.0f}m từ tâm — trong buffer 70m", pts)


def p_study_weak_gps(idx: int, rng: random.Random) -> Session:
    """
    Học 60 phút nhưng GPS indoor yếu — accuracy borderline 30-65m.
    Label=True: thực tế đang học, GPS yếu là vấn đề thiết bị.
    Pipeline có thể lọc nhiều điểm → FN nếu còn <5 điểm sạch.
    """
    pts = _study_gps(60, center_offset_m=rng.uniform(0, 10), rng=rng,
                     brownian_std_m=5.0,
                     accuracy_spike_prob=0.40,           # 40% spike
                     accuracy_spike_range=(45, 80),      # borderline
                     base_accuracy=(25, 50))              # base cũng cao hơn
    return Session(f"weak_gps_{idx}", "study_weak_gps", True, False,
                   "Học 60 phút, GPS indoor yếu (accuracy 25-80m, 40% spike)", pts)


def p_study_large_cafe(idx: int, rng: random.Random) -> Session:
    """
    Học ở quán lớn 2 tầng — GPS đôi khi lock outdoor khi gần cửa sổ, scatter 20-30m.
    Label=True: vẫn đang học dù GPS scatter.
    """
    pts = _study_gps(75, center_offset_m=rng.uniform(0, 15), rng=rng,
                     brownian_std_m=rng.uniform(8, 15),  # scatter lớn hơn
                     jump_prob=0.12,                      # jump nhiều hơn
                     jump_range_m=(10, 30))
    return Session(f"large_{idx}", "study_large_cafe", True, False,
                   "Học ở quán lớn, GPS scatter 8-15m Brownian + jump 12% tần suất", pts)


def p_study_multiple_breaks(idx: int, rng: random.Random) -> Session:
    """
    Học 90 phút, nghỉ 2 lần (ra ngoài quán).
    Label=True: tổng thời gian học > 60 phút.
    """
    breaks = [(20, 7), (55, 8)]  # (start_min, duration)
    pts = []
    for i in range(90):
        in_break = any(s <= i < s + d for s, d in breaks)
        if in_break:
            off = rng.uniform(60, 100)
            ang = rng.uniform(0, 2 * math.pi)
            lat = CAFE_LAT + off * math.cos(ang) * _LPM
            lng = CAFE_LNG + off * math.sin(ang) * _LGM
            pts.append(_pt(lat, lng, float(i), rng))
        else:
            pts += _study_gps(1, center_offset_m=rng.uniform(0, 8),
                               rng=rng, brownian_std_m=4.0, start_min=float(i))
    return Session(f"breaks_{idx}", "study_multiple_breaks", True, False,
                   "Học 90 phút, nghỉ 2 lần (7 và 8 phút) ra ngoài", pts)


# ──────────────────────────────────────────────
# FALSE profiles — người KHÔNG học
# ──────────────────────────────────────────────

def p_short_visit(idx: int, rng: random.Random) -> Session:
    """Ghé qua 5-18 phút — mua đồ uống rồi đi. Label=False."""
    n = rng.randint(5, 18)
    pts = _study_gps(n, center_offset_m=rng.uniform(0, 15), rng=rng,
                     brownian_std_m=4.0)
    return Session(f"short_{idx}", "short_visit", False, False,
                   f"Ghé qua {n} phút, lấy đồ uống rồi đi", pts)


def p_waiting_outside_buffer(idx: int, rng: random.Random) -> Session:
    """
    Đứng chờ bên ngoài quán 25-35 phút (trong vùng buffer 50-70m).
    Label=False: không trong quán, không học.
    ⚠️ Pipeline CÓ THỂ nói True vì GPS trong buffer zone — FP thực sự.
    """
    dist = rng.uniform(52, 68)    # trong buffer zone (50-70m)
    n    = rng.randint(25, 35)
    pts  = _outside_gps(n, dist, rng, spread_m=3.0)
    return Session(f"wait_buf_{idx}", "waiting_in_buffer", False, False,
                   f"Đứng chờ {n} phút cách {dist:.0f}m — trong buffer zone (52-68m), pipeline có thể nhầm", pts)


def p_waiting_outside_clear(idx: int, rng: random.Random) -> Session:
    """
    Đứng chờ rõ ràng ngoài quán 25-40 phút (>75m).
    Label=False. Pipeline nên nói False rõ ràng.
    """
    dist = rng.uniform(80, 150)
    n    = rng.randint(25, 40)
    pts  = _outside_gps(n, dist, rng, spread_m=4.0)
    return Session(f"wait_out_{idx}", "waiting_outside", False, False,
                   f"Đứng chờ {n} phút cách {dist:.0f}m — rõ ràng ngoài quán", pts)


def p_sleeping_in_cafe(idx: int, rng: random.Random) -> Session:
    """
    Ngủ trong quán 25-50 phút.
    Label=False: không học.
    ⚠️ GPS giống hệt học → ambiguous=True, pipeline KHÔNG THỂ phân biệt.
    """
    n   = rng.randint(25, 50)
    pts = _study_gps(n, center_offset_m=rng.uniform(0, 10), rng=rng,
                     brownian_std_m=3.0)  # nằm yên → drift nhỏ hơn
    return Session(f"sleep_{idx}", "sleeping_in_cafe", False, True,
                   f"Ngủ {n} phút trong quán — GPS giống học, pipeline không phân biệt được", pts)


def p_continuous_movement(idx: int, rng: random.Random) -> Session:
    """
    Di chuyển liên tục trong/ngoài quán — không dừng đủ lâu.
    Label=False.
    """
    lat, lng = CAFE_LAT, CAFE_LNG
    pts = []
    for i in range(60):
        step = rng.uniform(20, 45)
        ang  = rng.uniform(0, 2 * math.pi)
        lat += step * math.cos(ang) * _LPM
        lng += step * math.sin(ang) * _LGM
        pts.append(_pt(lat, lng, float(i), rng))
    return Session(f"move_{idx}", "continuous_movement", False, False,
                   "Di chuyển 20-45m mỗi phút — không dừng học", pts)


def p_meeting_in_cafe(idx: int, rng: random.Random) -> Session:
    """
    Gặp gỡ/họp 30-45 phút trong quán — không học.
    Label=False.
    ⚠️ GPS giống học → ambiguous=True.
    """
    n   = rng.randint(30, 45)
    pts = _study_gps(n, center_offset_m=rng.uniform(0, 12), rng=rng,
                     brownian_std_m=5.0)
    return Session(f"meet_{idx}", "meeting_in_cafe", False, True,
                   f"Họp/gặp gỡ {n} phút trong quán — GPS giống học", pts)


def p_walk_past(idx: int, rng: random.Random) -> Session:
    """
    Đi ngang qua quán, dừng lại <10 phút.
    Label=False.
    """
    n   = rng.randint(3, 10)
    pts = _study_gps(n, center_offset_m=rng.uniform(0, 20), rng=rng,
                     brownian_std_m=6.0)
    return Session(f"pass_{idx}", "walk_past", False, False,
                   f"Đi ngang qua, dừng {n} phút", pts)


# =============================================================================
# Profile distribution
# =============================================================================

TRUE_PROFILES = [
    (p_ideal_study,             0.28),
    (p_study_with_toilet_break, 0.10),
    (p_study_borderline_duration, 0.07),
    (p_study_near_window,       0.07),
    (p_study_weak_gps,          0.08),
    (p_study_large_cafe,        0.07),
    (p_study_multiple_breaks,   0.08),
]  

FALSE_PROFILES = [
    (p_short_visit,             0.10),
    (p_waiting_outside_buffer,  0.07),  # source of real FP
    (p_waiting_outside_clear,   0.07),
    (p_sleeping_in_cafe,        0.06),  # ambiguous
    (p_continuous_movement,     0.06),
    (p_meeting_in_cafe,         0.05),  # ambiguous
    (p_walk_past,               0.06),
]  


def build_dataset(n_total: int, rng: random.Random) -> List[Session]:
    sessions = []
    idx = 0
    for gen_fn, ratio in TRUE_PROFILES + FALSE_PROFILES:
        count = max(1, round(n_total * ratio))
        for _ in range(count):
            sessions.append(gen_fn(idx, random.Random(rng.randint(0, 2**31))))
            idx += 1
    rng.shuffle(sessions)
    return sessions


# =============================================================================
# Evaluation
# =============================================================================

def _run_pipeline(s: Session) -> dict:
    parsed   = validate_and_parse_gps_points(s.gps_points)
    ann, smm = apply_noise_filter(parsed, CAFE_LAT, CAFE_LNG, CAFE_RADIUS)
    clean    = get_clean_points(ann)
    result   = run_st_dbscan(clean, CAFE_LAT, CAFE_LNG, CAFE_RADIUS)
    result["_clean_count"] = smm["clean_count"]
    result["_total_count"] = smm["total_points"]
    return result


def evaluate(sessions: List[Session]) -> dict:
    records = []
    t_start = time.perf_counter()

    for s in sessions:
        t0  = time.perf_counter()
        res = _run_pipeline(s)
        ms  = (time.perf_counter() - t0) * 1000

        pred    = bool(res.get("is_studying", False))
        correct = (pred == s.true_label)
        records.append({
            "session_id":      s.sid,
            "profile":         s.profile,
            "true_label":      s.true_label,
            "pred_label":      pred,
            "correct":         correct,
            "ambiguous":       s.ambiguous,
            "reason":          res.get("reason"),
            "stable_dur_min":  res.get("stable_duration_min", 0.0),
            "dominant_pct":    res.get("dominant_cluster_pct", 0.0),
            "spatial_std_m":   res.get("spatial_std_m"),
            "clean_count":     res["_clean_count"],
            "total_count":     res["_total_count"],
            "note":            s.note,
            "elapsed_ms":      round(ms, 2),
        })

    total_ms = (time.perf_counter() - t_start) * 1000

    # All sessions (bao gồm ambiguous)
    TP = sum(1 for r in records if r["true_label"] and r["pred_label"])
    FP = sum(1 for r in records if not r["true_label"] and r["pred_label"])
    FN = sum(1 for r in records if r["true_label"] and not r["pred_label"])
    TN = sum(1 for r in records if not r["true_label"] and not r["pred_label"])

    # Non-ambiguous only (đánh giá fair hơn)
    na = [r for r in records if not r["ambiguous"]]
    TP_na = sum(1 for r in na if r["true_label"] and r["pred_label"])
    FP_na = sum(1 for r in na if not r["true_label"] and r["pred_label"])
    FN_na = sum(1 for r in na if r["true_label"] and not r["pred_label"])
    TN_na = sum(1 for r in na if not r["true_label"] and not r["pred_label"])

    def _metrics(tp, fp, fn, tn):
        total   = tp + fp + fn + tn
        acc     = (tp + tn) / total if total else 0
        prec    = tp / (tp + fp) if (tp + fp) else 0
        rec     = tp / (tp + fn) if (tp + fn) else 0
        f1      = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
        return dict(accuracy=acc, precision=prec, recall=rec, f1=f1,
                    TP=tp, FP=fp, FN=fn, TN=tn, total=total)

    # Per-profile stats
    pstats = {}
    for r in records:
        p = r["profile"]
        if p not in pstats:
            pstats[p] = {"total": 0, "correct": 0, "fp": 0, "fn": 0,
                         "true_label": r["true_label"], "ambiguous": r["ambiguous"]}
        pstats[p]["total"]   += 1
        pstats[p]["correct"] += int(r["correct"])
        if not r["true_label"] and r["pred_label"]: pstats[p]["fp"] += 1
        if r["true_label"] and not r["pred_label"]: pstats[p]["fn"] += 1

    return {
        "all":             _metrics(TP, FP, FN, TN),
        "non_ambiguous":   _metrics(TP_na, FP_na, FN_na, TN_na),
        "n_ambiguous":     sum(1 for r in records if r["ambiguous"]),
        "total_ms":        round(total_ms, 1),
        "avg_ms":          round(total_ms / len(records), 2) if records else 0,
        "profile_stats":   pstats,
        "records":         records,
    }


# =============================================================================
# Report
# =============================================================================

def print_report(res: dict) -> None:
    W  = 66
    ma = res["all"]
    mn = res["non_ambiguous"]

    print("\n" + "═" * W)
    print("  REALISTIC EVALUATION — ST-DBSCAN (is_studying)")
    print("  StudyCafe Analytics System — Scoring Engine v2.0.0")
    print("═" * W)

    print(f"\n  Tổng sessions      : {ma['total']}")
    print(f"  Ambiguous sessions : {res['n_ambiguous']}  "
          f"(pipeline không thể phân biệt về nguyên tắc)")
    print(f"  Non-ambiguous      : {mn['total']}")
    print(f"  Thời gian          : {res['total_ms']:.0f}ms "
          f"({res['avg_ms']:.1f}ms/session)")

    # ── Two sets of metrics ───────────────────────────────────────────────────
    for label, m in [("Tất cả sessions (kể cả ambiguous)", ma),
                     ("Non-ambiguous only (đánh giá fair)", mn)]:
        print(f"\n{'─'*W}")
        print(f"  {label}")
        print(f"{'─'*W}")
        print(f"  {'':18s} {'Pred TRUE':>10} {'Pred FALSE':>12}")
        print(f"  {'Actual TRUE':18s} {'TP='+str(m['TP']):>10} {'FN='+str(m['FN']):>12}")
        print(f"  {'Actual FALSE':18s} {'FP='+str(m['FP']):>10} {'TN='+str(m['TN']):>12}")
        print()
        targets = [("Accuracy", 0.85), ("Precision", 0.80),
                   ("Recall",   0.75), ("F1 Score", 0.78)]
        for mname, thresh in targets:
            val  = m[mname.lower().replace(" ", "_").replace("_score", "")]
            bar  = "█" * int(val * 30) + "░" * (30 - int(val * 30))
            note = "✓" if val >= thresh else "✗"
            print(f"  {mname:12s} {val:.4f}  [{bar}]  {note} ≥{thresh}")

    # ── Per-profile ───────────────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print("  Kết quả theo Profile")
    print(f"{'─'*W}")
    print(f"  {'Profile':30s} {'GT':5} {'Ambi':5} {'Acc':>6} {'FP':>4} {'FN':>4}")
    print("  " + "-" * 58)
    for prof, st in sorted(res["profile_stats"].items()):
        acc   = st["correct"] / st["total"] if st["total"] else 0
        gt    = "TRUE " if st["true_label"] else "FALSE"
        ambi  = "Y" if st["ambiguous"] else "N"
        bar   = "●" * st["correct"] + "○" * (st["total"] - st["correct"])
        print(f"  {prof:30s} {gt}  {ambi:5}  {acc:5.0%}  {st['fp']:>3}  {st['fn']:>3}  {bar}")

    # ── Errors ───────────────────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print("  Chi tiết lỗi (top 10)")
    print(f"{'─'*W}")
    errors = [r for r in res["records"] if not r["correct"]]
    if not errors:
        print("  Không có lỗi nào.")
    else:
        for r in errors[:10]:
            kind = "FP" if r["pred_label"] else "FN"
            ambi = " [AMBIGUOUS]" if r["ambiguous"] else ""
            print(f"  {kind}{ambi} | {r['session_id']:20s} | "
                  f"stable={r['stable_dur_min']:.0f}min "
                  f"pct={r['dominant_pct']:.2f} "
                  f"reason={r['reason']}")
            print(f"       ↳ {r['note']}")

    # ── Nhận xét ─────────────────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print("  Nhận xét và giới hạn thuật toán")
    print(f"{'─'*W}")
    fp_buf = [r for r in res["records"]
              if r["profile"] == "waiting_in_buffer" and not r["correct"]]
    ambi_fp = [r for r in res["records"]
               if r["ambiguous"] and not r["true_label"] and r["pred_label"]]

    if fp_buf:
        print(f"  ⚠  FP từ buffer zone ({len(fp_buf)} sessions):")
        print(f"     Người đứng ngoài quán 52–68m bị nhận nhầm là học.")
        print(f"     Nguyên nhân: RADIUS_BUFFER_M=20m quá rộng.")
        print(f"     Fix gợi ý: giảm RADIUS_BUFFER_M từ 20m → 10m,")
        print(f"     hoặc tăng MIN_STABLE_DURATION_MIN từ 20 → 25 phút.")

    if ambi_fp:
        print(f"  ⚠  FP từ ambiguous sessions ({len(ambi_fp)} sessions):")
        print(f"     Ngủ/họp trong quán GPS giống học — fundamental limitation.")
        print(f"     Không thể fix bằng hyperparameter — cần sensor bổ sung.")

    fn_list = [r for r in res["records"] if r["true_label"] and not r["pred_label"]]
    if fn_list:
        print(f"  ⚠  FN ({len(fn_list)} sessions): học thật bị bỏ sót.")
        for r in fn_list[:3]:
            print(f"     {r['session_id']}: clean={r['clean_count']}/{r['total_count']}"
                  f" reason={r['reason']}")

    # ── Verdict ──────────────────────────────────────────────────────────────
    f1_na = mn["f1"]
    print(f"\n{'─'*W}")
    if   f1_na >= 0.88: verdict = "GOOD — Đạt mức acceptable cho prototype."
    elif f1_na >= 0.78: verdict = "FAIR — Cần tune hyperparameter trước field test."
    else:               verdict = "POOR — Cần review lại logic hoặc threshold."
    print(f"  Verdict (non-ambiguous F1={f1_na:.4f}): {verdict}")
    print(f"\n  LƯU Ý: Đây vẫn là synthetic data với noise mô phỏng.")
    print(f"  Precision/Recall thực tế cần field test với GPS điện thoại thật.")
    print("═" * W + "\n")


def export_csv(res: dict, path: str) -> None:
    fields = ["session_id", "profile", "true_label", "pred_label", "correct",
              "ambiguous", "reason", "stable_dur_min", "dominant_pct",
              "spatial_std_m", "clean_count", "total_count", "note", "elapsed_ms"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(res["records"])
    print(f"  CSV → {path}")


# =============================================================================
# Main
# =============================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n",    type=int, default=200)
    ap.add_argument("--seed", type=int, default=2024)
    ap.add_argument("--csv",  action="store_true")
    ap.add_argument("--csv-path", default="realistic_eval_results.csv")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    print(f"\nBuilding realistic dataset (n≈{args.n}, seed={args.seed})...")
    sessions = build_dataset(args.n, rng)

    n_true  = sum(1 for s in sessions if s.true_label)
    n_false = sum(1 for s in sessions if not s.true_label)
    n_ambi  = sum(1 for s in sessions if s.ambiguous)
    print(f"  TRUE={n_true}  FALSE={n_false}  AMBIGUOUS={n_ambi}")

    print("Running pipeline...")
    result = evaluate(sessions)
    print_report(result)

    if args.csv:
        export_csv(result, args.csv_path)


if __name__ == "__main__":
    main()
