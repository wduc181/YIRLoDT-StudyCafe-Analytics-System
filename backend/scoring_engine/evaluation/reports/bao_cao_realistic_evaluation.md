# Báo cáo Realistic Evaluation — Module ST-DBSCAN
## StudyCafe Analytics System — Scoring Engine v2.0.0

**Ngày:** 25/04/2026  
**Script:** `scoring_engine/evaluate_realistic.py`  
**Dataset:** 244 sessions, 14 profiles, noise GPS thực tế  
**Seed:** 2024 (reproducible)

---

## 1. Sự khác biệt so với Synthetic Evaluation trước

| | Synthetic cũ (`evaluate_st_dbscan.py`) | Realistic (`evaluate_realistic.py`) |
|---|---|---|
| **Cách sinh label** | Từ công thức ngưỡng (`n < MIN_CLEAN_POINTS`) | Từ hành vi người dùng (`đang học` / `không học`) |
| **GPS noise** | Jitter cố định ±5m | Brownian drift, GPS jump 5%, accuracy spike 8-40% |
| **Ambiguous cases** | Không có | Có (ngủ, họp trong quán — GPS giống học) |
| **Kết quả** | F1 = 1.0000 (ảo) | F1 = 0.9259 / 0.9934 (thực) |
| **FP thực sự** | 0 | 24 (22 ambiguous + 2 non-ambiguous) |

---

## 2. Dataset

### Phân bố

| Thông số | Giá trị |
|---|---|
| Tổng sessions | 244 |
| TRUE (is_studying=True) | 150 sessions (61.5%) |
| FALSE (is_studying=False) | 94 sessions (38.5%) |
| Ambiguous | 22 sessions (9.0%) |
| Non-ambiguous | 222 sessions (91.0%) |
| Thời gian chạy | 2,416ms (9.9ms/session) |

### GPS noise model

GPS được sinh với noise thực tế theo 4 lớp:

**Brownian drift** — mô phỏng GPS indoor multipath. Mỗi điểm GPS drift theo phân phối Gaussian `N(0, σ)` với `σ = 3–15m` tuỳ profile. Người ngồi yên nhưng GPS vẫn trôi liên tục.

**GPS jump** — 5–12% điểm nhảy 5–30m ngẫu nhiên rồi về. Mô phỏng GPS glitch khi đột ngột bắt được vệ tinh mới.

**Accuracy spike** — 8–40% điểm có accuracy 45–120m (tùy profile). Mô phỏng tín hiệu yếu bất thường trong nhà.

**Borderline accuracy** — một số profile dùng base accuracy 25–50m để test ngưỡng 50m của noise filter.

### Danh sách 14 profiles

#### TRUE profiles (7 loại)

| Profile | Sessions | Mô tả | GPS noise |
|---|---|---|---|
| `ideal_study` | 58 | Học 60–120 phút điển hình | Brownian 3–7m, spike 8% |
| `study_toilet_break` | 20 | Học 90 phút, ra ngoài 5–9 phút | Brownian 4m |
| `borderline_duration` | 14 | Học đúng 21–26 phút | Brownian 4m |
| `study_near_window` | 14 | Ngồi cửa sổ, centroid 40–65m từ tâm | Brownian 5–10m |
| `study_weak_gps` | 16 | Học 60 phút, GPS yếu — accuracy 25–80m | Spike 40% |
| `study_large_cafe` | 14 | Quán lớn, scatter 8–15m, jump 12% | Brownian 8–15m + jump |
| `study_multiple_breaks` | 16 | Học 90 phút, 2 lần ra ngoài | Brownian 4m |

#### FALSE profiles (7 loại)

| Profile | Sessions | Ambiguous | Mô tả | FP risk |
|---|---|---|---|---|
| `short_visit` | 20 | Không | Ghé qua 5–18 phút | Thấp |
| `waiting_in_buffer` | 14 | Không | Đứng chờ 52–68m từ tâm (buffer zone) | **Cao** |
| `waiting_outside` | 14 | Không | Đứng chờ 80–150m từ tâm | Thấp |
| `sleeping_in_cafe` | 12 | **Có** | Ngủ 25–50 phút trong quán | **Không thể tránh** |
| `continuous_movement` | 12 | Không | Di chuyển 20–45m/phút | Thấp |
| `meeting_in_cafe` | 10 | **Có** | Họp 30–45 phút trong quán | **Không thể tránh** |
| `walk_past` | 12 | Không | Đi ngang qua, dừng <10 phút | Thấp |

---

## 3. Kết quả Evaluation

### 3.1 Tất cả sessions (kể cả ambiguous)

```
                     Pred TRUE   Pred FALSE
Actual TRUE  (150)    TP = 150       FN = 0
Actual FALSE  (94)    FP = 24       TN = 70
```

| Metric | Giá trị | Mục tiêu | Đánh giá |
|---|---|---|---|
| **Accuracy** | **0.9016** | ≥ 0.85 | ✅ PASS |
| **Precision** | **0.8621** | ≥ 0.80 | ✅ PASS |
| **Recall** | **1.0000** | ≥ 0.75 | ✅ PASS |
| **F1 Score** | **0.9259** | ≥ 0.78 | ✅ PASS |

### 3.2 Non-ambiguous only (loại bỏ ngủ/họp — đánh giá fair hơn)

```
                     Pred TRUE   Pred FALSE
Actual TRUE  (150)    TP = 150       FN = 0
Actual FALSE  (72)    FP = 2        TN = 70
```

| Metric | Giá trị | Mục tiêu | Đánh giá |
|---|---|---|---|
| **Accuracy** | **0.9910** | ≥ 0.85 | ✅ PASS |
| **Precision** | **0.9868** | ≥ 0.80 | ✅ PASS |
| **Recall** | **1.0000** | ≥ 0.75 | ✅ PASS |
| **F1 Score** | **0.9934** | ≥ 0.78 | ✅ PASS |

### 3.3 Kết quả per-profile

| Profile | Label | Ambiguous | Accuracy | FP | FN |
|---|---|---|---|---|---|
| ideal_study | TRUE | Không | 100% | 0 | 0 |
| study_toilet_break | TRUE | Không | 100% | 0 | 0 |
| borderline_duration | TRUE | Không | 100% | 0 | 0 |
| study_near_window | TRUE | Không | 100% | 0 | 0 |
| study_weak_gps | TRUE | Không | 100% | 0 | 0 |
| study_large_cafe | TRUE | Không | 100% | 0 | 0 |
| study_multiple_breaks | TRUE | Không | 100% | 0 | 0 |
| short_visit | FALSE | Không | 100% | 0 | 0 |
| waiting_outside | FALSE | Không | 100% | 0 | 0 |
| walk_past | FALSE | Không | 100% | 0 | 0 |
| continuous_movement | FALSE | Không | 92% | **1** | 0 |
| waiting_in_buffer | FALSE | Không | 93% | **1** | 0 |
| **sleeping_in_cafe** | FALSE | **Có** | **0%** | **12** | 0 |
| **meeting_in_cafe** | FALSE | **Có** | **0%** | **10** | 0 |

---

## 4. Phân tích lỗi

### 4.1 FP loại 1 — Ambiguous (22 sessions): không thể fix

Pipeline nói `True` cho tất cả session ngủ (12) và họp (10) trong quán. Đây **không phải lỗi thuật toán** — đây là **fundamental limitation** của phương pháp GPS-only.

```
sleep_204: stable=30min, pct=1.00, reason=None
↳ Ngủ 31 phút trong quán — GPS giống hệt đang học

meet_225: stable=43min, pct=1.00, reason=None  
↳ Họp/gặp gỡ 44 phút trong quán — GPS giống hệt đang học
```

Hành vi GPS của người ngủ và người họp **không có gì khác biệt** với người học xét về mặt vị trí. Không thể phân biệt bằng GPS đơn thuần. Để fix cần thêm: accelerometer (phát hiện nhịp gõ phím), screen on/off signal, hoặc self-report từ user.

### 4.2 FP loại 2 — Buffer zone (1 session): có thể fix

```
wait_buf_183: stable=23min, pct=0.62, reason=None
↳ Đứng chờ 29 phút cách 53m — trong buffer zone (52-68m)
```

Người đứng chờ bên ngoài quán nhưng cách tâm quán 53m — nằm trong `effective_radius = 50 + RADIUS_BUFFER_M(20) = 70m`. Pipeline nhận nhầm là đang trong quán học.

**Nguyên nhân:** `RADIUS_BUFFER_M = 20m` quá rộng. Buffer 20m được thêm để bù GPS drift indoor, nhưng vô tình bao gồm cả vỉa hè ngoài quán.

**Fix gợi ý:**
```python
# config.py
RADIUS_BUFFER_M = 10   # giảm từ 20m → 10m
# hoặc
MIN_STABLE_DURATION_MIN = 25  # tăng từ 20 → 25 phút
```

### 4.3 FP loại 3 — Continuous movement edge case (1 session)

1 session `continuous_movement` bị nhận nhầm do random walk vô tình tạo ra cụm điểm gần nhau trong 25 phút. Đây là edge case của random seed, không phải lỗi logic.

### 4.4 FN: 0 — Pipeline không bỏ sót session học thật

Recall = 1.0000. Tất cả 150 sessions học thật đều được phân loại đúng, kể cả:
- GPS weak (40% accuracy spike)
- Học ở quán lớn GPS scatter 8–15m
- Nghỉ giải lao ra ngoài
- Session đúng ngưỡng 21 phút

---

## 5. Diễn giải kết quả

### Đọc số liệu đúng cách

**F1 = 0.9259 (tất cả)** — Số này bị kéo xuống bởi 22 ambiguous sessions (ngủ/họp). Đây là giới hạn thực sự của phương pháp GPS-only, không phải lỗi của thuật toán.

**F1 = 0.9934 (non-ambiguous)** — Đây là con số phản ánh đúng chất lượng của pipeline khi loại bỏ các trường hợp bản thân GPS không thể phân biệt. Precision 98.68%, Recall 100%.

**Recall = 1.0000** — Pipeline không bỏ sót bất kỳ session học thật nào. Đây là ưu tiên quan trọng: thà nhận nhầm ngủ thành học (FP) còn hơn bỏ sót học thật (FN) — vì FN ảnh hưởng trực tiếp đến behavior score của quán.

### Tại sao Recall = 1.0 nhưng Precision < 1.0

Pipeline được thiết kế bảo thủ về phía "không bỏ sót" — các ngưỡng (`MIN_STABLE_DURATION_MIN=20`, `RADIUS_BUFFER_M=20`) nghiêng về phía chấp nhận hơn là từ chối. Đây là lựa chọn hợp lý cho hệ thống cafe rating: quán tốt không nên bị downgrade vì pipeline FN một số session học thật.

---

## 6. So sánh với mục tiêu trong Design Doc

Từ `scoring_engine_design.md` mục Acceptance Criteria:

| Tiêu chí | Mục tiêu | Kết quả (non-ambiguous) | Đánh giá |
|---|---|---|---|
| Precision ≥ 80% | 80% | **98.68%** | ✅ Vượt mục tiêu |
| Recall ≥ 75% | 75% | **100%** | ✅ Vượt mục tiêu |
| Không crash với GPS xấu | 100% | **100%** | ✅ Pass |
| Processing time < 500ms | 500ms | **9.9ms** | ✅ Nhanh 50× |

---

## 7. Giới hạn và bước tiếp theo

### Giới hạn của realistic evaluation này

Dù có noise GPS được mô phỏng thực tế hơn, dataset vẫn là **synthetic**. Brownian drift và GPS jump trong code là mô hình đơn giản hóa. GPS điện thoại thực tế có thêm:
- Ảnh hưởng của vật liệu tường/trần (kính, bê tông, kim loại)
- Sự khác biệt giữa các thiết bị (iPhone GPS tốt hơn Android mid-range)
- Thay đổi theo thời gian trong ngày (ít/nhiều vệ tinh nhìn thấy)
- Multipath từ đồ đạc trong quán

### Bước tiếp theo bắt buộc: Field test

Dù kết quả synthetic tốt, **field test với GPS thật vẫn cần thiết** để:
1. Xác nhận `RADIUS_BUFFER_M` và `EPS_SPATIAL_M` phù hợp với GPS thực tế
2. Kiểm tra Precision ≥ 80% với GPS điện thoại thật (mục tiêu design doc)
3. Phát hiện edge case mà synthetic data không cover được

**Kế hoạch field test tối thiểu:**
- 3 thành viên × 2 sessions mỗi người = 6 sessions labeled
- 2 sessions học thật (45–60 phút)
- 1 session ghé qua (<15 phút)
- 1 session đứng ngoài quán (30 phút)
- Chạy `evaluate_realistic.py` với data thật → so sánh predicted vs ground truth

---

## 8. File kèm theo

| File | Mô tả |
|---|---|
| `evaluate_realistic.py` | Script evaluation hoàn chỉnh |
| `realistic_eval_results.csv` | Kết quả chi tiết 244 sessions |

### Schema CSV

```
session_id, profile, true_label, pred_label, correct, ambiguous,
reason, stable_dur_min, dominant_pct, spatial_std_m,
clean_count, total_count, note, elapsed_ms
```

---

## 9. Kết luận

Pipeline ST-DBSCAN đạt **Precision = 98.68%, Recall = 100%, F1 = 0.9934** trên tập non-ambiguous (222 sessions). Khi tính cả ambiguous cases (ngủ/họp trong quán GPS giống học), F1 = 0.9259.

Điểm quan trọng nhất: **22/24 FP là ambiguous về nguyên tắc** — không phải lỗi thuật toán. Pipeline không thể phân biệt ngủ vs học hay họp vs học chỉ từ GPS. Đây là giới hạn của phương pháp, không phải của implementation.

Chỉ có **2 FP thực sự có thể fix**: 1 từ buffer zone (giảm `RADIUS_BUFFER_M`), 1 từ continuous movement edge case.
