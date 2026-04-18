"""
config.py — Tất cả hyperparameter và constants của Scoring Engine.

Chỉnh sửa file này để tune hành vi của toàn pipeline.
Không hardcode magic number ở bất kỳ file nào khác.
"""

# ============================================================
# Noise Filter
# ============================================================

# Lớp A: Accuracy threshold — điểm GPS có accuracy > ngưỡng này bị đánh dấu nhiễu
ACCURACY_THRESHOLD_M: float = 50.0

# Lớp B: Speed filter
SPEED_THRESHOLD_MS: float = 8.33      # 30 km/h — vi phạm vật lý khi ngồi học
MIN_TIME_DELTA_S: float = 5.0         # timestamp quá gần nhau → likely duplicate/cache

# Lớp C: Hampel Identifier
HAMPEL_WINDOW_K: int = 2              # cửa sổ mỗi phía k điểm → tổng cửa sổ 2k+1 = 5
HAMPEL_Z_THRESHOLD: float = 3.0       # ngưỡng z-score MAD để đánh dấu outlier

# Hard rule: điểm nằm ngoài cafe radius × 2 bị đánh dấu nhiễu geofence
GEOFENCE_MULTIPLIER: float = 2.0

# ============================================================
# ST-DBSCAN (Study Detection)
# ============================================================

EPS_SPATIAL_M: float = 25.0           # bán kính spatial tối đa trong 1 cluster (mét)
EPS_TEMPORAL_S: float = 600.0         # khoảng thời gian tối đa giữa 2 điểm cùng cluster (giây)
DBSCAN_MIN_SAMPLES: int = 3           # số điểm tối thiểu để tạo cluster

RADIUS_BUFFER_M: float = 20.0         # buffer thêm vào cafe.radius_meters để bù GPS drift
MIN_STABLE_DURATION_MIN: float = 20.0 # thời gian tối thiểu để coi là "đang học" (phút)
DOMINANT_CLUSTER_PCT: float = 0.60    # cluster phải chứa ≥ 60% điểm sạch
MAX_SPATIAL_STD_M: float = 30.0       # độ phân tán tối đa cho phép trong cluster (mét)

# Số điểm GPS tối thiểu sau lọc để chạy tiếp pipeline
MIN_CLEAN_POINTS: int = 5

# Số điểm GPS thô tối thiểu để bắt đầu pipeline
MIN_RAW_POINTS: int = 3

# ============================================================
# Feature Normalization
# ============================================================

NORM_MAX_DURATION_MIN: float = 180.0  # 3 tiếng = điểm f2 = 1.0
NORM_MAX_SPATIAL_STD_M: float = 30.0  # = eps DBSCAN = upper bound
DROPOFF_THRESHOLD_MIN: float = 30.0   # session < 30 phút → coi là rời sớm

# ============================================================
# Scoring Weights (tổng = 1.0)
# ============================================================

WEIGHTS: dict = {
    "study_rate":        0.30,   # f1 — tỷ lệ session is_studying=True
    "avg_stable_dur":    0.20,   # f2 — thời gian ổn định trung bình
    "spatial_stability": 0.15,   # f3 — độ ổn định không gian
    "clean_data_rate":   0.10,   # f4 — tỷ lệ dữ liệu GPS sạch
    "retention":         0.10,   # f5 — tỷ lệ không rời sớm
    "cluster_purity":    0.10,   # f6 — mật độ cluster
    "coverage_ratio":    0.05,   # f7 — tỷ lệ thời gian trong cluster
}

# ============================================================
# Bayesian Average
# ============================================================

MIN_CONFIDENT_SESSIONS: int = 5       # m: ngưỡng tin cậy (số session is_studying=True)
HAS_ENOUGH_DATA_THRESH: int = 5       # cùng giá trị — cần ≥ 5 studying session để has_enough_data=True
DEFAULT_SYSTEM_AVG: float = 6.5       # prior C khi chưa có system_avg_score
                                      # Khớp với default_prior trong scoring_service._get_cafe_history()

# Scale output về [0, 10]
SCORE_SCALE: float = 10.0

# ============================================================
# Engine metadata
# ============================================================

ENGINE_VERSION: str = "2.0.0"
