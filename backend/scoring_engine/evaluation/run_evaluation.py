"""
run_evaluation.py — All-in-one Evaluation Pipeline cho ST-DBSCAN.

Chạy một lệnh duy nhất, sinh ra toàn bộ output:
    1. dataset.csv          — toàn bộ dataset sinh ra (có thể mở Excel xem)
    2. dataset_sample.json  — 3 session mẫu để xem định dạng GPS data
    3. results.csv          — kết quả từng session sau khi chạy pipeline
    4. metrics_report.json  — tất cả metrics dạng JSON có thể đọc programmatically
    5. chart_confusion_matrix.png
    6. chart_metrics_overview.png
    7. chart_profile_accuracy.png
    8. chart_gps_scatter.png
    9. chart_stable_duration_dist.png
   10. chart_error_analysis.png

Cách chạy:
    cd backend/
    python scoring_engine/evaluation/run_evaluation.py
    python scoring_engine/evaluation/run_evaluation.py --n 200 --seed 2024
    python scoring_engine/evaluation/run_evaluation.py --out-dir my_results/
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scoring_engine import config
from scoring_engine.noise_filter import apply_noise_filter, get_clean_points
from scoring_engine.st_dbscan import run_st_dbscan
from scoring_engine.utils.validators import validate_and_parse_gps_points

# ── Constants ─────────────────────────────────────────────────────────────────
CAFE_LAT    = 21.0024
CAFE_LNG    = 105.8453
CAFE_RADIUS = 50.0
_LPM = 1.0 / 111_320.0
_LGM = 1.0 / (111_320.0 * math.cos(math.radians(CAFE_LAT)))
T0   = datetime(2026, 4, 10, 8, 0, 0, tzinfo=timezone.utc)


# =============================================================================
# Session dataclass
# =============================================================================

@dataclass
class Session:
    sid:         str
    profile:     str
    true_label:  bool
    ambiguous:   bool
    note:        str
    gps_points:  List[dict]


# =============================================================================
# GPS generators
# =============================================================================

def _pt(lat, lng, t_min, rng, acc_range=(10, 20)):
    return {
        "lat":       round(lat, 7),
        "lng":       round(lng, 7),
        "accuracy":  round(rng.uniform(*acc_range), 1),
        "timestamp": (T0 + timedelta(minutes=t_min)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _study_gps(n, offset_m=0.0, rng=None, std_m=5.0,
               jump_p=0.05, jump_r=(5, 20),
               spike_p=0.08, spike_r=(55, 120),
               base_acc=(10, 22), interval=1.0, start=0.0):
    pts = []
    blat = CAFE_LAT + offset_m * _LPM
    blng = CAFE_LNG
    for i in range(n):
        dlat = rng.gauss(0, std_m) * _LPM
        dlng = rng.gauss(0, std_m) * _LGM
        if rng.random() < jump_p:
            j = rng.uniform(*jump_r); a = rng.uniform(0, 2 * math.pi)
            dlat += j * math.cos(a) * _LPM; dlng += j * math.sin(a) * _LGM
        ar = spike_r if rng.random() < spike_p else base_acc
        pts.append(_pt(blat + dlat, blng + dlng, start + i * interval, rng, ar))
    return pts


def _outside_gps(n, offset_m, rng, spread=4.0, interval=1.0):
    pts = []
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi)
        plat = CAFE_LAT + offset_m * math.cos(a) * _LPM + rng.gauss(0, spread) * _LPM
        plng = CAFE_LNG + offset_m * math.sin(a) * _LGM + rng.gauss(0, spread) * _LGM
        pts.append(_pt(plat, plng, i * interval, rng))
    return pts


# =============================================================================
# Profile generators (14 profiles)
# =============================================================================

def p_ideal_study(idx, rng):
    n = rng.randint(60, 120)
    pts = _study_gps(n, rng.uniform(0, 10), rng, rng.uniform(3, 7))
    return Session(f"ideal_{idx}", "ideal_study", True, False,
                   f"Ngồi học {n} phút, brownian drift 3-7m, spike 8%", pts)


def p_toilet_break(idx, rng):
    bs = rng.randint(20, 60); bd = rng.randint(5, 9)
    pts = []
    for i in range(90):
        if bs <= i < bs + bd:
            off = rng.uniform(30, 80); a = rng.uniform(0, 2 * math.pi)
            pts.append(_pt(CAFE_LAT + off * math.cos(a) * _LPM + rng.gauss(0, 3) * _LPM,
                           CAFE_LNG + off * math.sin(a) * _LGM + rng.gauss(0, 3) * _LGM,
                           float(i), rng))
        else:
            pts += _study_gps(1, rng.uniform(0, 8), rng, 4.0, start=float(i))
    return Session(f"toilet_{idx}", "study_toilet_break", True, False,
                   f"Học 90 phút, nghỉ vệ sinh {bd} phút tại phút {bs}", pts)


def p_borderline_duration(idx, rng):
    n = rng.randint(21, 26)
    pts = _study_gps(n, rng.uniform(0, 8), rng, 4.0)
    return Session(f"bdur_{idx}", "borderline_duration", True, False,
                   f"Học {n} phút — vừa trên ngưỡng 20 phút", pts)


def p_near_window(idx, rng):
    off = rng.uniform(40, 65)
    pts = _study_gps(60, off, rng, rng.uniform(5, 10))
    return Session(f"win_{idx}", "study_near_window", True, False,
                   f"Ngồi cửa sổ, centroid≈{off:.0f}m từ tâm — trong buffer 70m", pts)


def p_weak_gps(idx, rng):
    pts = _study_gps(60, rng.uniform(0, 10), rng, 5.0,
                     spike_p=0.40, spike_r=(45, 80), base_acc=(25, 50))
    return Session(f"weak_{idx}", "study_weak_gps", True, False,
                   "Học 60 phút, GPS yếu — accuracy 25-80m, 40% spike", pts)


def p_large_cafe(idx, rng):
    pts = _study_gps(75, rng.uniform(0, 15), rng, rng.uniform(8, 15),
                     jump_p=0.12, jump_r=(10, 30))
    return Session(f"large_{idx}", "study_large_cafe", True, False,
                   "Quán lớn 2 tầng, GPS scatter 8-15m, jump 12%", pts)


def p_multi_breaks(idx, rng):
    pts = []
    for i in range(90):
        if any(s <= i < s + d for s, d in [(20, 7), (55, 8)]):
            off = rng.uniform(60, 100); a = rng.uniform(0, 2 * math.pi)
            pts.append(_pt(CAFE_LAT + off * math.cos(a) * _LPM,
                           CAFE_LNG + off * math.sin(a) * _LGM, float(i), rng))
        else:
            pts += _study_gps(1, rng.uniform(0, 8), rng, 4.0, start=float(i))
    return Session(f"brk_{idx}", "study_multiple_breaks", True, False,
                   "Học 90 phút, nghỉ 2 lần (7 và 8 phút) ra ngoài", pts)


def p_short_visit(idx, rng):
    n = rng.randint(5, 18)
    pts = _study_gps(n, rng.uniform(0, 15), rng, 4.0)
    return Session(f"short_{idx}", "short_visit", False, False,
                   f"Ghé qua {n} phút, lấy đồ uống rồi đi", pts)


def p_waiting_buffer(idx, rng):
    dist = rng.uniform(52, 68); n = rng.randint(25, 35)
    pts = _outside_gps(n, dist, rng, 3.0)
    return Session(f"wbuf_{idx}", "waiting_in_buffer", False, False,
                   f"Đứng chờ {n} phút cách {dist:.0f}m — buffer zone 52-68m", pts)


def p_waiting_outside(idx, rng):
    dist = rng.uniform(80, 150); n = rng.randint(25, 40)
    pts = _outside_gps(n, dist, rng, 4.0)
    return Session(f"wout_{idx}", "waiting_outside", False, False,
                   f"Đứng chờ {n} phút cách {dist:.0f}m — rõ ngoài quán", pts)


def p_sleeping(idx, rng):
    n = rng.randint(25, 50)
    pts = _study_gps(n, rng.uniform(0, 10), rng, 3.0)
    return Session(f"slp_{idx}", "sleeping_in_cafe", False, True,
                   f"Ngủ {n} phút trong quán — GPS giống học, không phân biệt được", pts)


def p_movement(idx, rng):
    lat, lng = CAFE_LAT, CAFE_LNG
    pts = []
    for i in range(60):
        step = rng.uniform(20, 45); a = rng.uniform(0, 2 * math.pi)
        lat += step * math.cos(a) * _LPM; lng += step * math.sin(a) * _LGM
        pts.append(_pt(lat, lng, float(i), rng))
    return Session(f"mov_{idx}", "continuous_movement", False, False,
                   "Di chuyển 20-45m/phút — không dừng", pts)


def p_meeting(idx, rng):
    n = rng.randint(30, 45)
    pts = _study_gps(n, rng.uniform(0, 12), rng, 5.0)
    return Session(f"meet_{idx}", "meeting_in_cafe", False, True,
                   f"Họp {n} phút trong quán — GPS giống học", pts)


def p_walk_past(idx, rng):
    n = rng.randint(3, 10)
    pts = _study_gps(n, rng.uniform(0, 20), rng, 6.0)
    return Session(f"pass_{idx}", "walk_past", False, False,
                   f"Đi ngang qua, dừng {n} phút", pts)


PROFILES = [
    (p_ideal_study,        0.28, True),
    (p_toilet_break,       0.10, True),
    (p_borderline_duration,0.07, True),
    (p_near_window,        0.07, True),
    (p_weak_gps,           0.08, True),
    (p_large_cafe,         0.07, True),
    (p_multi_breaks,       0.08, True),
    (p_short_visit,        0.10, False),
    (p_waiting_buffer,     0.07, False),
    (p_waiting_outside,    0.07, False),
    (p_sleeping,           0.06, False),
    (p_movement,           0.06, False),
    (p_meeting,            0.05, False),
    (p_walk_past,          0.06, False),
]


def build_dataset(n_total, rng):
    sessions = []
    idx = 0
    for gen_fn, ratio, _ in PROFILES:
        count = max(1, round(n_total * ratio))
        for _ in range(count):
            sessions.append(gen_fn(idx, random.Random(rng.randint(0, 2**31))))
            idx += 1
    rng.shuffle(sessions)
    return sessions


# =============================================================================
# Pipeline runner & evaluator
# =============================================================================

def _run_pipeline(s: Session):
    parsed = validate_and_parse_gps_points(s.gps_points)
    ann, smm = apply_noise_filter(parsed, CAFE_LAT, CAFE_LNG, CAFE_RADIUS)
    clean = get_clean_points(ann)
    result = run_st_dbscan(clean, CAFE_LAT, CAFE_LNG, CAFE_RADIUS)
    result["_clean"] = smm["clean_count"]
    result["_total"] = smm["total_points"]
    return result


def evaluate(sessions):
    records = []
    t0 = time.perf_counter()
    for s in sessions:
        ts = time.perf_counter()
        res = _run_pipeline(s)
        pred = bool(res.get("is_studying", False))
        records.append({
            "session_id":     s.sid,
            "profile":        s.profile,
            "true_label":     s.true_label,
            "pred_label":     pred,
            "correct":        pred == s.true_label,
            "ambiguous":      s.ambiguous,
            "reason":         res.get("reason"),
            "stable_dur_min": round(res.get("stable_duration_min", 0.0), 2),
            "dominant_pct":   round(res.get("dominant_cluster_pct", 0.0), 4),
            "spatial_std_m":  res.get("spatial_std_m"),
            "clean_count":    res["_clean"],
            "total_count":    res["_total"],
            "noise_rate":     round(1 - res["_clean"] / max(res["_total"], 1), 4),
            "n_gps_raw":      len(s.gps_points),
            "note":           s.note,
            "elapsed_ms":     round((time.perf_counter() - ts) * 1000, 2),
        })

    total_ms = (time.perf_counter() - t0) * 1000

    def _m(recs):
        TP = sum(1 for r in recs if r["true_label"] and r["pred_label"])
        FP = sum(1 for r in recs if not r["true_label"] and r["pred_label"])
        FN = sum(1 for r in recs if r["true_label"] and not r["pred_label"])
        TN = sum(1 for r in recs if not r["true_label"] and not r["pred_label"])
        tot = TP + FP + FN + TN
        prec = TP / (TP + FP) if (TP + FP) else 0
        rec  = TP / (TP + FN) if (TP + FN) else 0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
        return dict(TP=TP, FP=FP, FN=FN, TN=TN, total=tot,
                    accuracy=(TP+TN)/tot if tot else 0,
                    precision=prec, recall=rec, f1=f1)

    na = [r for r in records if not r["ambiguous"]]
    pstats = {}
    for r in records:
        p = r["profile"]
        if p not in pstats:
            pstats[p] = {"total": 0, "correct": 0, "FP": 0, "FN": 0,
                         "true_label": r["true_label"], "ambiguous": r["ambiguous"]}
        pstats[p]["total"]   += 1
        pstats[p]["correct"] += int(r["correct"])
        if not r["true_label"] and r["pred_label"]: pstats[p]["FP"] += 1
        if r["true_label"] and not r["pred_label"]: pstats[p]["FN"] += 1

    return {
        "all":           _m(records),
        "non_ambiguous": _m(na),
        "n_ambiguous":   sum(1 for r in records if r["ambiguous"]),
        "total_ms":      round(total_ms, 1),
        "avg_ms":        round(total_ms / len(records), 2),
        "profile_stats": pstats,
        "records":       records,
    }


# =============================================================================
# Exporters
# =============================================================================

def export_dataset_csv(sessions: List[Session], path: Path):
    """Xuất dataset — mỗi row là 1 session, GPS points được compact thành JSON string."""
    rows = []
    for s in sessions:
        rows.append({
            "session_id":     s.sid,
            "profile":        s.profile,
            "true_label":     s.true_label,
            "ambiguous":      s.ambiguous,
            "n_gps_points":   len(s.gps_points),
            "duration_min":   len(s.gps_points),   # 1 point/min
            "first_lat":      s.gps_points[0]["lat"],
            "first_lng":      s.gps_points[0]["lng"],
            "first_ts":       s.gps_points[0]["timestamp"],
            "last_ts":        s.gps_points[-1]["timestamp"],
            "avg_accuracy":   round(sum(p["accuracy"] for p in s.gps_points) / len(s.gps_points), 1),
            "note":           s.note,
            "gps_points_json": json.dumps(s.gps_points[:5]) + "...",  # preview 5 điểm đầu
        })
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"  ✓ dataset.csv             ({len(rows)} sessions)")


def export_dataset_sample_json(sessions: List[Session], path: Path):
    """Xuất 3 session mẫu dạng JSON đầy đủ để mentor xem định dạng GPS data."""
    # Lấy 1 TRUE, 1 FALSE non-ambiguous, 1 FALSE ambiguous
    sample_true  = next(s for s in sessions if s.true_label and not s.ambiguous)
    sample_false = next(s for s in sessions if not s.true_label and not s.ambiguous)
    sample_ambi  = next(s for s in sessions if s.ambiguous)

    doc = {
        "_description": "3 session mẫu đại diện cho từng loại trong dataset",
        "_format_note": "Đây chính xác là format input của pipeline ST-DBSCAN",
        "cafe_reference": {
            "center_lat": CAFE_LAT, "center_lng": CAFE_LNG,
            "radius_meters": CAFE_RADIUS,
            "effective_radius_m": CAFE_RADIUS + config.RADIUS_BUFFER_M,
        },
        "samples": [
            {
                "case":        "TRUE — Đang học (ideal_study)",
                "session_id":  sample_true.sid,
                "profile":     sample_true.profile,
                "true_label":  sample_true.true_label,
                "ambiguous":   sample_true.ambiguous,
                "note":        sample_true.note,
                "n_gps_points": len(sample_true.gps_points),
                "gps_points":  sample_true.gps_points[:10],
                "_note_gps":   f"Hiển thị 10/{len(sample_true.gps_points)} điểm đầu",
            },
            {
                "case":        "FALSE — Không học (short_visit)",
                "session_id":  sample_false.sid,
                "profile":     sample_false.profile,
                "true_label":  sample_false.true_label,
                "ambiguous":   sample_false.ambiguous,
                "note":        sample_false.note,
                "n_gps_points": len(sample_false.gps_points),
                "gps_points":  sample_false.gps_points,
            },
            {
                "case":        "FALSE/AMBIGUOUS — GPS giống học (sleeping_in_cafe)",
                "session_id":  sample_ambi.sid,
                "profile":     sample_ambi.profile,
                "true_label":  sample_ambi.true_label,
                "ambiguous":   sample_ambi.ambiguous,
                "note":        sample_ambi.note,
                "n_gps_points": len(sample_ambi.gps_points),
                "gps_points":  sample_ambi.gps_points[:10],
                "_why_ambiguous": "Pipeline không thể phân biệt ngủ vs học chỉ từ GPS",
            },
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"  ✓ dataset_sample.json     (3 session mẫu với GPS data đầy đủ)")


def export_results_csv(res: dict, path: Path):
    fields = ["session_id", "profile", "true_label", "pred_label", "correct",
              "ambiguous", "reason", "stable_dur_min", "dominant_pct",
              "spatial_std_m", "clean_count", "total_count", "noise_rate",
              "n_gps_raw", "note", "elapsed_ms"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(res["records"])
    print(f"  ✓ results.csv             ({len(res['records'])} records)")


def export_metrics_json(res: dict, sessions: List[Session], path: Path, seed: int):
    n_true  = sum(1 for s in sessions if s.true_label)
    n_false = sum(1 for s in sessions if not s.true_label)
    doc = {
        "metadata": {
            "generated_at":   datetime.now(timezone.utc).isoformat(),
            "engine_version": config.ENGINE_VERSION,
            "seed":           seed,
            "n_sessions":     len(sessions),
            "n_true_label":   n_true,
            "n_false_label":  n_false,
            "n_ambiguous":    res["n_ambiguous"],
            "n_non_ambiguous": res["non_ambiguous"]["total"],
        },
        "config_snapshot": {
            "MIN_CLEAN_POINTS":          config.MIN_CLEAN_POINTS,
            "MIN_STABLE_DURATION_MIN":   config.MIN_STABLE_DURATION_MIN,
            "EPS_SPATIAL_M":             config.EPS_SPATIAL_M,
            "EPS_TEMPORAL_S":            config.EPS_TEMPORAL_S,
            "DOMINANT_CLUSTER_PCT":      config.DOMINANT_CLUSTER_PCT,
            "RADIUS_BUFFER_M":           config.RADIUS_BUFFER_M,
            "MAX_SPATIAL_STD_M":         config.MAX_SPATIAL_STD_M,
            "ACCURACY_THRESHOLD_M":      config.ACCURACY_THRESHOLD_M,
            "SPEED_THRESHOLD_MS":        config.SPEED_THRESHOLD_MS,
        },
        "metrics_all_sessions": {
            k: round(v, 4) if isinstance(v, float) else v
            for k, v in res["all"].items()
        },
        "metrics_non_ambiguous": {
            k: round(v, 4) if isinstance(v, float) else v
            for k, v in res["non_ambiguous"].items()
        },
        "performance": {
            "total_time_ms": res["total_ms"],
            "avg_time_ms_per_session": res["avg_ms"],
        },
        "profile_breakdown": {
            p: {**st, "accuracy": round(st["correct"] / st["total"], 4) if st["total"] else 0}
            for p, st in res["profile_stats"].items()
        },
        "error_analysis": {
            "FP_total":            res["all"]["FP"],
            "FP_ambiguous":        sum(1 for r in res["records"]
                                       if r["ambiguous"] and not r["true_label"] and r["pred_label"]),
            "FP_non_ambiguous":    sum(1 for r in res["records"]
                                       if not r["ambiguous"] and not r["true_label"] and r["pred_label"]),
            "FN_total":            res["all"]["FN"],
            "FP_by_profile":       {
                p: st["FP"] for p, st in res["profile_stats"].items() if st["FP"] > 0
            },
            "FN_by_profile":       {
                p: st["FN"] for p, st in res["profile_stats"].items() if st["FN"] > 0
            },
        },
        "verdict": (
            "GOOD — Đạt mức acceptable cho prototype."
            if res["non_ambiguous"]["f1"] >= 0.88
            else "FAIR — Cần tune hyperparameter."
        ),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"  ✓ metrics_report.json     (metrics + config snapshot + error analysis)")


# =============================================================================
# Charts
# =============================================================================

def make_charts(res: dict, sessions: List[Session], charts_dir: Path):
    # charts_dir = results/run_.../charts/ — tất cả PNG save vào đây
    out_dir = charts_dir  # alias để không đổi tên biến bên trong
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.gridspec as gridspec
    import numpy as np

    COLORS = {
        "green":  "#2E7D32",
        "red":    "#C62828",
        "blue":   "#1565C0",
        "orange": "#E65100",
        "gray":   "#616161",
        "light_green": "#A5D6A7",
        "light_red":   "#EF9A9A",
        "light_blue":  "#90CAF9",
    }
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.spines.top":   False,
        "axes.spines.right": False,
        "figure.dpi":        150,
    })

    records   = res["records"]
    ma        = res["all"]
    mn        = res["non_ambiguous"]

    # ─────────────────────────────────────────────────────────────────────────
    # Chart 1: Confusion Matrix (2 views side-by-side)
    # ─────────────────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Confusion Matrix — ST-DBSCAN is_studying Classification",
                 fontsize=13, fontweight="bold", y=1.02)

    for ax, m, title in [
        (axes[0], ma, f"Tất cả sessions (n={ma['total']})"),
        (axes[1], mn, f"Non-ambiguous only (n={mn['total']})"),
    ]:
        cm = np.array([[m["TP"], m["FN"]], [m["FP"], m["TN"]]])
        im = ax.imshow(cm, cmap="Blues", vmin=0)
        ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
        ax.set_xticklabels(["Pred TRUE", "Pred FALSE"], fontsize=11)
        ax.set_yticklabels(["Actual TRUE", "Actual FALSE"], fontsize=11)
        ax.set_title(title, fontsize=11, pad=10)
        for i in range(2):
            for j in range(2):
                label = ["TP", "FN", "FP", "TN"][i * 2 + j]
                color = "white" if cm[i, j] > cm.max() * 0.6 else "black"
                ax.text(j, i, f"{label}\n{cm[i,j]}",
                        ha="center", va="center", fontsize=14,
                        fontweight="bold", color=color)

        metrics_text = (f"Accuracy:  {m['accuracy']:.4f}\n"
                        f"Precision: {m['precision']:.4f}\n"
                        f"Recall:    {m['recall']:.4f}\n"
                        f"F1 Score:  {m['f1']:.4f}")
        ax.text(1.25, 0.5, metrics_text, transform=ax.transAxes,
                fontsize=10, va="center", fontfamily="monospace",
                bbox=dict(boxstyle="round", facecolor="#F5F5F5", alpha=0.8))

    plt.tight_layout()
    p = out_dir / "chart_01_confusion_matrix.png"
    plt.savefig(p, bbox_inches="tight"); plt.close()
    print(f"  ✓ chart_01_confusion_matrix.png")

    # ─────────────────────────────────────────────────────────────────────────
    # Chart 2: Metrics Overview — bar chart 4 metrics × 2 conditions
    # ─────────────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 5))
    metric_names = ["Accuracy", "Precision", "Recall", "F1 Score"]
    metric_keys  = ["accuracy", "precision", "recall", "f1"]
    thresholds   = [0.85, 0.80, 0.75, 0.78]
    vals_all = [ma[k] for k in metric_keys]
    vals_na  = [mn[k] for k in metric_keys]

    x = np.arange(len(metric_names)); w = 0.3
    bars1 = ax.bar(x - w/2, vals_all, w, label="Tất cả (kể cả ambiguous)",
                   color=COLORS["light_blue"], edgecolor=COLORS["blue"], linewidth=1.2)
    bars2 = ax.bar(x + w/2, vals_na,  w, label="Non-ambiguous only",
                   color=COLORS["light_green"], edgecolor=COLORS["green"], linewidth=1.2)

    # Value labels
    for bar in list(bars1) + list(bars2):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{bar.get_height():.4f}", ha="center", va="bottom", fontsize=9)

    # Threshold lines
    for i, (thresh, name) in enumerate(zip(thresholds, metric_names)):
        ax.hlines(thresh, i - 0.4, i + 0.4, colors=COLORS["red"],
                  linestyles="--", linewidth=1.2, alpha=0.7)
        ax.text(i + 0.42, thresh, f"≥{thresh}", va="center",
                fontsize=8, color=COLORS["red"])

    ax.set_ylim(0, 1.12)
    ax.set_xticks(x); ax.set_xticklabels(metric_names, fontsize=11)
    ax.set_ylabel("Score"); ax.set_title("Metrics Overview — ST-DBSCAN Evaluation",
                                         fontsize=12, fontweight="bold")
    ax.legend(fontsize=10); ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    p = out_dir / "chart_02_metrics_overview.png"
    plt.savefig(p, bbox_inches="tight"); plt.close()
    print(f"  ✓ chart_02_metrics_overview.png")

    # ─────────────────────────────────────────────────────────────────────────
    # Chart 3: Per-profile Accuracy
    # ─────────────────────────────────────────────────────────────────────────
    pstats  = res["profile_stats"]
    prof_names = sorted(pstats.keys())
    accs    = [pstats[p]["correct"] / pstats[p]["total"] for p in prof_names]
    labels_gt = [("TRUE" if pstats[p]["true_label"] else "FALSE") for p in prof_names]
    ambis   = [pstats[p]["ambiguous"] for p in prof_names]
    colors  = []
    for p, is_ambi in zip(prof_names, ambis):
        if is_ambi:      colors.append(COLORS["orange"])
        elif pstats[p]["true_label"]: colors.append(COLORS["green"])
        else:            colors.append(COLORS["blue"])

    fig, ax = plt.subplots(figsize=(12, 5))
    bars = ax.barh(prof_names, accs, color=colors, edgecolor="white", linewidth=0.5)
    for bar, acc, n in zip(bars, accs,
                           [pstats[p]["total"] for p in prof_names]):
        ax.text(min(acc + 0.01, 0.98), bar.get_y() + bar.get_height() / 2,
                f"{acc:.0%}  (n={n})", va="center", fontsize=9)
    ax.axvline(1.0, color=COLORS["gray"], linestyle="--", alpha=0.5)
    ax.set_xlim(0, 1.15)
    ax.set_xlabel("Accuracy per Profile")
    ax.set_title("Accuracy theo Profile — ST-DBSCAN", fontsize=12, fontweight="bold")
    legend_patches = [
        mpatches.Patch(color=COLORS["green"],  label="TRUE  label (học)"),
        mpatches.Patch(color=COLORS["blue"],   label="FALSE label (không học)"),
        mpatches.Patch(color=COLORS["orange"], label="AMBIGUOUS (GPS không phân biệt được)"),
    ]
    ax.legend(handles=legend_patches, fontsize=9, loc="lower right")
    ax.grid(axis="x", alpha=0.3); plt.tight_layout()
    p = out_dir / "chart_03_profile_accuracy.png"
    plt.savefig(p, bbox_inches="tight"); plt.close()
    print(f"  ✓ chart_03_profile_accuracy.png")

    # ─────────────────────────────────────────────────────────────────────────
    # Chart 4: GPS Scatter — 4 profile mẫu
    # ─────────────────────────────────────────────────────────────────────────
    sample_profiles = [
        ("ideal_study",        "Học lý tưởng (TRUE)"),
        ("short_visit",        "Ghé qua (FALSE)"),
        ("waiting_in_buffer",  "Đứng ngoài quán (FALSE - FP risk)"),
        ("sleeping_in_cafe",   "Ngủ trong quán (AMBIGUOUS)"),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    fig.suptitle("GPS Scatter — Mẫu 4 Profile (50 điểm đầu)",
                 fontsize=12, fontweight="bold")

    # Build lookup session by profile
    prof_lookup: dict[str, Session] = {}
    for s in sessions:
        if s.profile not in prof_lookup:
            prof_lookup[s.profile] = s

    for ax, (pname, ptitle) in zip(axes, sample_profiles):
        s = prof_lookup.get(pname)
        if s is None:
            ax.set_visible(False); continue
        pts = s.gps_points[:50]
        lats = [(p["lat"] - CAFE_LAT) / _LPM for p in pts]
        lngs = [(p["lng"] - CAFE_LNG) / _LGM for p in pts]
        accs = [p["accuracy"] for p in pts]

        sc = ax.scatter(lngs, lats, c=accs, cmap="RdYlGn_r",
                        vmin=10, vmax=80, s=25, alpha=0.8, zorder=3)
        # Cafe center
        ax.scatter(0, 0, c="black", s=80, marker="*", zorder=5, label="Tâm quán")
        # Cafe radius circles
        for r, ls, lbl in [(50, "-", "radius 50m"), (70, "--", "+buffer 70m")]:
            theta = np.linspace(0, 2 * np.pi, 200)
            ax.plot(r * np.cos(theta), r * np.sin(theta),
                    color="#9E9E9E", linestyle=ls, linewidth=1, alpha=0.6)
        # Color by index (time)
        ax.set_title(ptitle, fontsize=9, fontweight="bold")
        ax.set_xlabel("Δ lng (m)", fontsize=8); ax.set_ylabel("Δ lat (m)", fontsize=8)
        ax.set_aspect("equal"); ax.grid(alpha=0.2)

        # Label label
        lcolor = COLORS["orange"] if s.ambiguous else (COLORS["green"] if s.true_label else COLORS["red"])
        ltext  = "AMBIGUOUS" if s.ambiguous else ("TRUE" if s.true_label else "FALSE")
        ax.text(0.03, 0.97, ltext, transform=ax.transAxes, fontsize=9,
                color=lcolor, fontweight="bold", va="top")

    plt.colorbar(sc, ax=axes[-1], label="GPS Accuracy (m)", shrink=0.8)
    plt.tight_layout()
    p = out_dir / "chart_04_gps_scatter.png"
    plt.savefig(p, bbox_inches="tight"); plt.close()
    print(f"  ✓ chart_04_gps_scatter.png")

    # ─────────────────────────────────────────────────────────────────────────
    # Chart 5: Stable Duration Distribution (TRUE vs FALSE)
    # ─────────────────────────────────────────────────────────────────────────
    dur_true_correct = [r["stable_dur_min"] for r in records
                        if r["true_label"] and r["correct"]]
    dur_false_fp     = [r["stable_dur_min"] for r in records
                        if not r["true_label"] and r["pred_label"]]
    dur_true_fn      = [r["stable_dur_min"] for r in records
                        if r["true_label"] and not r["pred_label"]]

    fig, ax = plt.subplots(figsize=(10, 4))
    bins = np.linspace(0, 130, 30)
    ax.hist(dur_true_correct, bins=bins, alpha=0.7,
            color=COLORS["green"], label=f"TRUE — Đúng (n={len(dur_true_correct)})")
    if dur_false_fp:
        ax.hist(dur_false_fp, bins=bins, alpha=0.7,
                color=COLORS["red"], label=f"FALSE — FP (n={len(dur_false_fp)})")
    if dur_true_fn:
        ax.hist(dur_true_fn, bins=bins, alpha=0.7,
                color=COLORS["orange"], label=f"TRUE — FN bị bỏ sót (n={len(dur_true_fn)})")
    ax.axvline(config.MIN_STABLE_DURATION_MIN, color="black", linestyle="--",
               linewidth=1.5, label=f"MIN_STABLE_DURATION={config.MIN_STABLE_DURATION_MIN}min")
    ax.set_xlabel("Stable Duration (phút)"); ax.set_ylabel("Số sessions")
    ax.set_title("Phân phối Stable Duration — TRUE vs FP vs FN",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    p = out_dir / "chart_05_stable_duration_dist.png"
    plt.savefig(p, bbox_inches="tight"); plt.close()
    print(f"  ✓ chart_05_stable_duration_dist.png")

    # ─────────────────────────────────────────────────────────────────────────
    # Chart 6: Error Analysis — FP breakdown + noise rate
    # ─────────────────────────────────────────────────────────────────────────
    fp_ambi  = sum(1 for r in records
                   if r["ambiguous"] and not r["true_label"] and r["pred_label"])
    fp_buf   = sum(1 for r in records
                   if r["profile"] == "waiting_in_buffer" and not r["correct"])
    fp_other = ma["FP"] - fp_ambi - fp_buf

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    fig.suptitle("Error Analysis", fontsize=12, fontweight="bold")

    # FP breakdown pie
    ax = axes[0]
    fp_vals   = [fp_ambi, fp_buf, fp_other]
    fp_labels = [f"Ambiguous\n(ngủ/họp)\nn={fp_ambi}",
                 f"Buffer zone FP\n(52-68m)\nn={fp_buf}",
                 f"Other\nn={fp_other}"]
    fp_colors = [COLORS["orange"], COLORS["red"], COLORS["gray"]]
    non_zero  = [(v, l, c) for v, l, c in zip(fp_vals, fp_labels, fp_colors) if v > 0]
    if non_zero:
        vals, lbls, clrs = zip(*non_zero)
        wedges, texts, autotexts = ax.pie(
            vals, labels=lbls, colors=clrs, autopct="%1.0f%%",
            startangle=140, pctdistance=0.75,
            wedgeprops={"edgecolor": "white", "linewidth": 2})
        for at in autotexts: at.set_fontsize(10); at.set_fontweight("bold")
    ax.set_title(f"Phân tích {ma['FP']} False Positive", fontsize=11, fontweight="bold")

    # Noise rate by profile
    ax = axes[1]
    noise_by_profile = {}
    for r in records:
        p = r["profile"]
        if p not in noise_by_profile:
            noise_by_profile[p] = []
        noise_by_profile[p].append(r["noise_rate"])
    pnames  = sorted(noise_by_profile.keys())
    n_means = [np.mean(noise_by_profile[p]) * 100 for p in pnames]
    bar_c   = [COLORS["green"] if res["profile_stats"][p]["true_label"]
               else (COLORS["orange"] if res["profile_stats"][p]["ambiguous"]
               else COLORS["blue"]) for p in pnames]
    bars = ax.barh(pnames, n_means, color=bar_c, edgecolor="white")
    for bar, v in zip(bars, n_means):
        ax.text(v + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{v:.1f}%", va="center", fontsize=8)
    ax.set_xlabel("Tỷ lệ GPS noise trung bình (%)"); ax.set_xlim(0, max(n_means) * 1.25)
    ax.set_title("Noise Rate theo Profile", fontsize=11, fontweight="bold")
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    p = out_dir / "chart_06_error_analysis.png"
    plt.savefig(p, bbox_inches="tight"); plt.close()
    print(f"  ✓ chart_06_error_analysis.png")

    # ─────────────────────────────────────────────────────────────────────────
    # Chart 7: Dataset Overview — profile distribution + label split
    # ─────────────────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Dataset Overview", fontsize=12, fontweight="bold")

    # Label split donut
    ax = axes[0]
    n_true  = sum(1 for s in sessions if s.true_label)
    n_false = sum(1 for s in sessions if not s.true_label)
    n_ambi  = res["n_ambiguous"]
    sizes   = [n_true, n_false - n_ambi, n_ambi]
    labels  = [f"TRUE\n(học thật)\nn={n_true}",
               f"FALSE\n(non-ambiguous)\nn={n_false - n_ambi}",
               f"FALSE\n(ambiguous)\nn={n_ambi}"]
    clrs    = [COLORS["green"], COLORS["blue"], COLORS["orange"]]
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=clrs, autopct="%1.1f%%",
        startangle=90, pctdistance=0.78,
        wedgeprops={"edgecolor": "white", "linewidth": 2, "width": 0.6})
    for at in autotexts: at.set_fontsize(10); at.set_fontweight("bold")
    ax.set_title(f"Phân bố Label (n={len(sessions)} sessions)", fontsize=11, fontweight="bold")

    # Profile count bar
    ax = axes[1]
    pnames  = sorted(res["profile_stats"].keys())
    pcounts = [res["profile_stats"][p]["total"] for p in pnames]
    pclrs   = [COLORS["green"] if res["profile_stats"][p]["true_label"]
               else (COLORS["orange"] if res["profile_stats"][p]["ambiguous"]
               else COLORS["blue"]) for p in pnames]
    bars = ax.barh(pnames, pcounts, color=pclrs, edgecolor="white")
    for bar, n in zip(bars, pcounts):
        ax.text(n + 0.3, bar.get_y() + bar.get_height() / 2,
                str(n), va="center", fontsize=9)
    ax.set_xlabel("Số sessions"); ax.set_xlim(0, max(pcounts) * 1.2)
    ax.set_title("Sessions theo Profile", fontsize=11, fontweight="bold")
    legend_patches = [
        mpatches.Patch(color=COLORS["green"],  label="TRUE (học)"),
        mpatches.Patch(color=COLORS["blue"],   label="FALSE (không học)"),
        mpatches.Patch(color=COLORS["orange"], label="AMBIGUOUS"),
    ]
    ax.legend(handles=legend_patches, fontsize=9)
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    p = out_dir / "chart_07_dataset_overview.png"
    plt.savefig(p, bbox_inches="tight"); plt.close()
    print(f"  ✓ chart_07_dataset_overview.png")


# =============================================================================
# Main
# =============================================================================

def main():
    ap = argparse.ArgumentParser(
        description="All-in-one evaluation pipeline cho ST-DBSCAN"
    )
    ap.add_argument("--n",       type=int, default=200, help="Số sessions (default: 200)")
    ap.add_argument("--seed",    type=int, default=2024, help="Random seed (default: 2024)")
    ap.add_argument("--out-dir", type=str, default=None,
                    help="Thư mục gốc output (default: evaluation/results/run_YYYYMMDD_HHMMSS/)")
    args = ap.parse_args()

    # ── Directory structure ───────────────────────────────────────────────────
    # evaluation/
    # ├── data/                        ← dataset đầu vào (không thay đổi theo run)
    # │   ├── dataset.csv
    # │   └── dataset_sample.json
    # └── results/
    #     └── run_YYYYMMDD_HHMMSS_seedX_nY/   ← mỗi lần chạy tạo 1 folder mới
    #         ├── results.csv
    #         ├── metrics_report.json
    #         └── charts/
    #             ├── chart_01_confusion_matrix.png
    #             ├── ...
    #             └── chart_07_dataset_overview.png

    base = Path(__file__).parent

    # data/ — dùng chung, không tạo lại mỗi lần chạy (trừ khi seed thay đổi)
    data_dir = base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # results/run_.../ — mỗi lần chạy tạo mới
    if args.out_dir:
        run_dir = Path(args.out_dir)
    else:
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = base / "results" / f"run_{ts}_seed{args.seed}_n{args.n}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # charts/ nằm trong run_dir
    charts_dir = run_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  ST-DBSCAN Evaluation Pipeline")
    print(f"  seed={args.seed}  n≈{args.n}")
    print(f"  data/    → {data_dir}")
    print(f"  results/ → {run_dir}")
    print(f"  charts/  → {charts_dir}")
    print(f"{'='*60}")

    # ── 1. Build dataset ──────────────────────────────────────────────────────
    rng = random.Random(args.seed)
    print(f"\n[1/4] Generating dataset...")
    sessions = build_dataset(args.n, rng)
    n_true  = sum(1 for s in sessions if s.true_label)
    n_false = sum(1 for s in sessions if not s.true_label)
    n_ambi  = sum(1 for s in sessions if s.ambiguous)
    print(f"      {len(sessions)} sessions — TRUE={n_true}, FALSE={n_false}, AMBIGUOUS={n_ambi}")

    # ── 2. Export dataset → data/ ─────────────────────────────────────────────
    print(f"\n[2/4] Exporting dataset files → data/...")
    export_dataset_csv(sessions,         data_dir / "dataset.csv")
    export_dataset_sample_json(sessions, data_dir / "dataset_sample.json")

    # ── 3. Run pipeline ───────────────────────────────────────────────────────
    print(f"\n[3/4] Running pipeline ({len(sessions)} sessions)...")
    result = evaluate(sessions)
    ma, mn = result["all"], result["non_ambiguous"]
    print(f"      Done in {result['total_ms']:.0f}ms ({result['avg_ms']:.1f}ms/session)")
    print(f"\n      ┌─ ALL ──── Acc={ma['accuracy']:.4f}  P={ma['precision']:.4f}"
          f"  R={ma['recall']:.4f}  F1={ma['f1']:.4f}")
    print(f"      └─ NON-AMB  Acc={mn['accuracy']:.4f}  P={mn['precision']:.4f}"
          f"  R={mn['recall']:.4f}  F1={mn['f1']:.4f}")

    # ── 4. Export results → run_dir/, charts → charts_dir/ ───────────────────
    print(f"\n[4/4] Exporting results & charts...")
    export_results_csv(result,                                run_dir / "results.csv")
    export_metrics_json(result, sessions, run_dir / "metrics_report.json", args.seed)
    make_charts(result, sessions,                             charts_dir)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Cấu trúc output:")
    print(f"")
    print(f"  evaluation/data/")
    for f in sorted(data_dir.iterdir()):
        print(f"    ├── {f.name:<40s} {f.stat().st_size/1024:>6.1f} KB")
    print(f"")
    print(f"  evaluation/results/{run_dir.name}/")
    for f in sorted(run_dir.iterdir()):
        if f.is_file():
            print(f"    ├── {f.name:<40s} {f.stat().st_size/1024:>6.1f} KB")
    print(f"    └── charts/")
    for f in sorted(charts_dir.iterdir()):
        print(f"         ├── {f.name:<36s} {f.stat().st_size/1024:>6.1f} KB")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
