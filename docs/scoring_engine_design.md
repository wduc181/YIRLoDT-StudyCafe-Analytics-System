# Scoring Engine Design Document
## StudyCafe Analytics System

**Phiên bản:** v1.0  
**Ngày cập nhật:** 18/04/2026  

---

## 1. Mục tiêu module

Module **Scoring Engine** là thành phần trí tuệ cốt lõi của hệ thống, đóng vai trò "bộ não" chuyển hóa dữ liệu GPS thô *(Raw Spatio-temporal Data)* thành chỉ số chất lượng địa điểm học tập có ý nghĩa.

Module giải quyết bốn vấn đề cụ thể:

1. **Lọc nhiễu GPS** — khử các điểm bất thường do multipath, drift trong nhà, và yếu tín hiệu trước khi phân tích.
2. **Phát hiện hành vi học tập** — phân biệt chính xác giữa "ngồi học thực sự" với "ghé qua", "gặp gỡ", hoặc "đi lại liên tục" thông qua phân cụm không gian–thời gian.
3. **Trích xuất đặc trưng hành vi** — lượng hóa thời gian ổn định, mức độ di chuyển, tính liên tục và đặc trưng rời sớm từ mỗi session.
4. **Tính điểm hành vi quán** — tổng hợp nhiều session thành một Behavior Score phản ánh trải nghiệm cộng đồng thực tế, không phụ thuộc vào cảm tính cá nhân.

Giá trị cốt lõi của module: điểm số phản ánh **hành vi khách quan của nhiều người dùng thực tế**, không phải một review chủ quan hay check-in đơn lẻ.

---

## 2. Phạm vi và giới hạn

### 2.1 Trong phạm vi
- Nhận GPS logs của một session từ backend qua function call (Python embedded module).
- Lọc nhiễu GPS bằng kỹ thuật thống kê kết hợp Hampel Identifier.
- Phân cụm không gian–thời gian để phát hiện "điểm dừng" (Stay-point detection) bằng ST-DBSCAN.
- Trích xuất feature vector mô tả hành vi của session.
- Phân loại session: `STUDY` / `NON_STUDY`.
- Tính Behavior Score cho từng quán bằng Weighted Scoring + Bayesian Average.
- Hỗ trợ cả real-time (tính ngay sau 1 session) và batch (tính lại toàn bộ).
- Trả kết quả về backend qua return value — backend tự persist vào DB.

### 2.2 Ngoài phạm vi
- Không trực tiếp ghi vào database.
- Không xử lý authentication hay session management.
- Không phân tích nội dung hoạt động (app đang dùng, loại âm thanh, v.v.).
- Không cá nhân hóa score theo từng user (điểm là của **quán**, không phải của user).
- Không xử lý real-time streaming từng giây — chỉ xử lý session đã kết thúc.

### 2.3 Giả định
- GPS được gửi định kỳ mỗi **60 giây** trong suốt session.
- Accuracy GPS dao động từ **5m đến 50m** trong điều kiện bình thường; trên 50m là kém tin cậy.
- Session hợp lệ để tính điểm tối thiểu là **20 phút** (20 điểm GPS sau lọc).
- Tọa độ trung tâm quán (`center_lat`, `center_lng`, `radius_meters`) đã được hardcode và chính xác.
- Trong giai đoạn demo: pipeline là **hoàn toàn unsupervised** — không có ground truth label.
- Dữ liệu mock và dữ liệu thật được xử lý bằng cùng một pipeline.

---

## 3. Input Contract

### 3.1 Nguồn dữ liệu

Backend gọi module **sau khi session kết thúc** (`POST /api/session/end`). Module được import như một Python package vào cùng process với backend — không có HTTP call nội bộ.

```
Backend process
    └── from scoring_engine import score_session, update_cafe_score
    └── session_result = score_session(payload)
    └── cafe_result   = update_cafe_score(cafe_id, session_result, history)
    └── db.save(session_result, cafe_result)
```

Kiến trúc **embedded module** phù hợp quy mô demo 3 thành viên và loại bỏ overhead của microservice.

### 3.2 Format dữ liệu đầu vào
```python
{
    "session_id":  "uuid-string",          # bắt buộc
    "device_id":   "device-001",           # bắt buộc
    "cafe": {
        "cafe_id":        1,               # bắt buộc
        "center_lat":     21.0285,         # bắt buộc
        "center_lng":     105.8542,        # bắt buộc
        "radius_meters":  50               # bắt buộc
    },
    "gps_points": [                        # bắt buộc, list ít nhất 1 phần tử
        {
            "lat":       21.0285,          # bắt buộc
            "lng":       105.8542,         # bắt buộc
            "accuracy":  12.5,             # optional (mét); null nếu thiết bị không cung cấp
            "timestamp": "2026-04-07T09:01:00Z"  # bắt buộc, ISO 8601
        },
        ...
    ]
}
```

### 3.3 Dữ liệu tham chiếu cần thêm

Backend truyền thêm lịch sử điểm của quán để module có thể cập nhật Bayesian score:

```python
{
    # ... (như trên)
    "cafe_history": {
        "total_sessions_processed": 12,   # số session đã tính trước đó; 0 nếu quán mới
        "current_score":            7.4,  # điểm hiện tại, null nếu chưa có
        "studying_session_count":   9,    # số session is_studying=True
        "system_avg_score":         6.5   # điểm trung bình toàn hệ thống (dùng cho Bayesian prior)
    }
}
```

> Nếu `cafe_history` vắng mặt → module vẫn chạy nhưng chỉ trả kết quả session-level, không cập nhật cafe score.

---

## 4. Pipeline tổng thể

```
Raw GPS Input  {lat, lng, accuracy, timestamp} × N
    │
    ▼
┌───────────────────────────────────────────────────────┐
│  Bước 1: Validation & Preprocessing                   │
│  - Parse và sort timestamp tăng dần                   │
│  - Tính time_delta giữa các điểm liên tiếp            │
│  - Kiểm tra đủ điểm tối thiểu (≥ 3 điểm thô)         │
└──────────────────────────┬────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────┐
│  Bước 2: Noise Filter (3 lớp tuần tự)                 │
│  Lớp A: Accuracy threshold  (lọc cứng ≥ 50m)         │
│  Lớp B: Speed filter        (vật lý, Haversine)       │
│  Lớp C: Hampel Identifier   (sliding MAD, thống kê)   │
│  → Đánh dấu is_noise = True, KHÔNG xóa               │
└──────────────────────────┬────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────┐
│  Bước 3: ST-DBSCAN Clustering                         │
│  - Phân cụm trên (lat, lng) × timestamp               │
│  - eps_spatial = 25m, eps_temporal = 600s             │
│  - Xác định dominant Stay-point                       │
│  - Kiểm tra Stay-point có nằm trong cafe radius       │
│  - Tính stable_duration                               │
└──────────────────────────┬────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────┐
│  Bước 4: Feature Extraction                           │
│  - Tính 8 features mô tả hành vi                      │
│  - Normalize về [0, 1]                                │
└──────────────────────────┬────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────┐
│  Bước 5: Session Scoring                              │
│  - Weighted sum → session_score ∈ [0, 1]              │
│  - Gán nhãn is_studying True/False                    │
└──────────────────────────┬────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────┐
│  Bước 6: Cafe Score Update (Bayesian Average)         │
│  - Kết hợp session mới với prior lịch sử quán         │
│  - Kiểm tra has_enough_data threshold                 │
└──────────────────────────┬────────────────────────────┘
                           │
                           ▼
                    Output Score Dict
```

---

## 5. Noise Filter

### 5.1 Vấn đề cần giải quyết

GPS trên smartphone trong môi trường quán cafe có bốn loại nhiễu chính:

| Loại nhiễu | Biểu hiện | Nguyên nhân |
|---|---|---|
| **GPS Jump** | Tọa độ nhảy đột ngột 200–500m rồi quay lại | Multipath reflection từ tường/trần |
| **Accuracy Spike** | `accuracy` = 150–300m | Yếu tín hiệu vệ tinh, che khuất trong nhà |
| **Indoor Drift** | Vị trí trôi dần 20–40m dù ngồi yên | Nhiễu không đồng đều khi ở trong nhà |
| **Stale Cache** | Timestamp quá gần nhau (< 5s) | GPS API trả về dữ liệu cache |

Nếu không lọc, các điểm nhiễu làm sai lệch kết quả clustering và phân loại hành vi.

### 5.2 Thuật toán / Phương pháp chọn

Sử dụng **3 lớp lọc tuần tự** từ đơn giản đến phức tạp:

**Lớp A — Accuracy Threshold Filter (cứng)**
Loại trực tiếp theo field `accuracy` từ GPS API. Điểm có `accuracy > 50m` bị đánh dấu nhiễu.
Chi phí O(n), loại được phần lớn nhiễu nặng trong một pass.

**Lớp B — Speed Filter (vật lý)**
Tính tốc độ di chuyển giữa hai điểm liên tiếp bằng Haversine:

```python
speed_ms = haversine_m(p[i], p[i+1]) / time_delta_s
if speed_ms > SPEED_THRESHOLD_MS:   # mặc định 8.33 m/s = 30 km/h
    p[i+1].is_noise = True
```

Vi phạm vật lý (không thể di chuyển 30 km/h khi đang ngồi trong quán) là dấu hiệu rõ ràng của GPS glitch.

**Lớp C — Hampel Identifier (thống kê, sliding window)**
Hampel Identifier dùng **Median Absolute Deviation (MAD)** trên cửa sổ trượt để phát hiện outlier cục bộ — bắt được indoor drift từ từ mà speed filter bỏ qua:

```python
# Với cửa sổ k = 5 (mỗi phía 2 điểm):
for i in range(k, n-k):
    window = coords[i-k : i+k+1]
    median = np.median(window)
    mad    = np.median(np.abs(window - median))
    scale  = 1.4826 * mad      # hệ số chuẩn hóa MAD → std
    if abs(coords[i] - median) > Z_THRESHOLD * scale:
        points[i].is_noise = True
```

**Lý do chọn Hampel thay vì Z-score thuần hay Kalman Filter:**
- Hampel dùng **median** thay vì mean → robust hơn với outlier chùm (chuỗi điểm nhiễu liên tiếp).
- Không cần giả định mô hình vật lý (như Kalman cần Constant Velocity model) — phù hợp vì người học thực tế ngồi yên, thỉnh thoảng đứng dậy, hành vi không đều.
- Nhẹ hơn Kalman Filter, không có dependency phức tạp, dễ debug.

> **Ghi chú v2.0:** Kalman Filter (đề xuất trong bản 2 và bản 3 của các AI khác) là lựa chọn tốt cho GPS tracking liên tục theo chuyển động. Tuy nhiên trong bài toán này người dùng chủ yếu **đứng yên**, nên Hampel Identifier trên cửa sổ trượt phù hợp hơn và cho kết quả tương đương với ít dependency hơn.

### 5.3 Tiêu chí đánh dấu là nhiễu

| Điều kiện | Ngưỡng | Lớp |
|---|---|---|
| `accuracy > 50` | 50m | A |
| `speed > 8.33 m/s` | 30 km/h | B |
| `time_delta < 5s` | 5 giây — likely duplicate | B |
| `|coord - median_window| > 3 × MAD × 1.4826` | z = 3 | C |
| Nằm ngoài `radius_meters × 2` từ tâm quán | khoảng cách > 2× radius | Hard rule |

### 5.4 Output của bước này

```python
[
    {
        "lat":         21.0285,
        "lng":         105.8542,
        "accuracy":    12.5,
        "timestamp":   "2026-04-07T09:01:00Z",
        "is_noise":    False,
        "noise_reason": None    # hoặc "accuracy" | "speed" | "duplicate" | "hampel" | "geofence"
    },
    ...
]

# Kèm summary:
{
    "total_points":  120,
    "noise_count":   12,
    "clean_count":   108,
    "clean_rate":    0.90
}
```

Điểm nhiễu **không bị xóa** — chỉ đánh dấu `is_noise = True` để giữ audit trail và debug.

### 5.5 Edge cases cần xử lý

| Tình huống | Xử lý |
|---|---|
| Tất cả điểm đều là nhiễu | Trả `{"is_studying": False, "reason": "all_noise"}`, không crash |
| Dưới 5 điểm sạch sau lọc | Trả `has_enough_data: False` |
| `accuracy = null` | Bỏ qua lớp A, vẫn chạy lớp B và C |
| Timestamp không tăng đơn điệu | Sort lại trước khi tính speed |

---

## 6. Study Detection

### 6.1 Định nghĩa "đang học" trong hệ thống này

**Ngôn ngữ tự nhiên:**
Một session được coi là "đang học" nếu người dùng **ở yên tại một vị trí ổn định trong thời gian dài**, vị trí đó **nằm trong phạm vi quán**, và không có dấu hiệu di chuyển liên tục hoặc rời sớm.

**Điều kiện toán học (tất cả phải thỏa mãn):**

```
C1: Tồn tại ít nhất 1 Stay-point cluster chứa ≥ 60% số điểm GPS sạch.

C2: Centroid của dominant cluster ≤ (cafe.radius_meters + 20m) so với (center_lat, center_lng).
    (buffer 20m bù trừ GPS drift khi ngồi sát cửa hoặc ngoài hiên)

C3: Thời gian liên tục trong cluster (stable_duration) ≥ 20 phút.

C4: Độ phân tán trong cluster (spatial_std) ≤ 30m.
    (bù đắp GPS indoor drift mà không cho phép di chuyển thực sự)
```

**`is_studying = True` khi C1 ∧ C2 ∧ C3 ∧ C4 đều thỏa mãn.**

### 6.2 Thuật toán: ST-DBSCAN (Spatio-Temporal DBSCAN)

Thay vì DBSCAN không gian thuần túy, module sử dụng **ST-DBSCAN** — phiên bản mở rộng xem xét đồng thời cả khoảng cách không gian lẫn thời gian.

**Lý do chọn ST-DBSCAN thay vì DBSCAN thông thường:**
- DBSCAN thường sẽ **gộp nhầm** hai lần người dùng ngồi cùng chỗ nhưng cách nhau nhiều giờ (ví dụ: sáng học, về nhà, chiều quay lại) thành một cluster duy nhất → inflate stable_duration sai.
- ST-DBSCAN thêm điều kiện `eps_temporal`: hai điểm chỉ được vào cùng cluster nếu **cả khoảng cách lẫn khoảng thời gian** đều trong ngưỡng cho phép.
- Không cần biết trước số cluster.
- Tự động nhận diện điểm đi lại lẻ tẻ (đi vệ sinh, lấy nước) là noise (label = -1).

**Triển khai:**

```python
# Mỗi điểm sạch được biểu diễn bởi (lat_rad, lng_rad, timestamp_s_normalized)
# Dùng custom metric kết hợp Haversine + temporal distance

def st_distance(p1, p2, alpha=EPS_SPATIAL_M, beta=EPS_TEMPORAL_S):
    spatial  = haversine_m(p1[:2], p2[:2])
    temporal = abs(p1[2] - p2[2])             # delta giây
    # Normalize về [0,1] rồi lấy max
    return max(spatial / alpha, temporal / beta)

# DBSCAN với custom metric, eps = 1.0 (điểm trong threshold ở cả 2 chiều)
db = DBSCAN(eps=1.0, min_samples=MIN_SAMPLES, metric=st_distance)
labels = db.fit_predict(feature_matrix)
```

### 6.3 Parameters và lý do chọn

| Parameter | Giá trị | Giải thích |
|---|---|---|
| `eps_spatial` | 25m | Bán kính spatial của cluster. 25m bù đắp GPS indoor drift (10–20m) có buffer. Nhỏ hơn 30m để tránh merge hai khu vực ngồi khác nhau trong quán lớn |
| `eps_temporal` | 600s (10 phút) | Khoảng cách thời gian tối đa giữa 2 điểm cùng cluster. Đủ bao gồm khoảng nghỉ ngắn (đi vệ sinh) mà không gộp nhầm hai lần học khác nhau |
| `min_samples` | 3 | Tối thiểu 3 điểm GPS (≈ 3 phút) để tạo cluster. Tránh noise 1–2 điểm bị cluster sai |
| `min_stable_duration` | 20 phút | Ngưỡng tối thiểu để xem là "đang học". Lọc được khách ghé qua |
| `dominant_cluster_pct` | 60% | Cluster phải chứa ≥ 60% điểm sạch mới được coi là Stay-point chính |
| `radius_buffer` | 20m | Buffer thêm vào `cafe.radius_meters` để bù GPS drift |
| `max_spatial_std` | 30m | Giới hạn trên của phân tán trong cluster (= eps DBSCAN) |

### 6.4 Output của bước này

```python
{
    "cluster_labels":               [0, 0, -1, 0, 1, 0, ...],  # -1 = noise ST-DBSCAN
    "dominant_cluster_id":          0,
    "dominant_cluster_point_count": 85,
    "dominant_cluster_pct":         0.87,
    "dominant_cluster_centroid": {
        "lat": 21.02851,
        "lng": 105.85423
    },
    "centroid_distance_to_cafe_m":  18.3,
    "is_within_cafe_radius":        True,
    "stable_duration_min":          87.0,
    "spatial_std_m":                8.4,    # std khoảng cách các điểm trong cluster đến centroid
    "coverage_ratio":               0.87,   # % thời gian trong cluster / tổng thời gian session
    "is_studying":                  True
}
```

### 6.5 Edge cases cần xử lý

| Tình huống | Xử lý |
|---|---|
| Session quá ngắn (< 20 phút) | `is_studying = False`, `reason = "too_short"`. Không chạy ST-DBSCAN |
| Không có cluster nào (tất cả = noise label) | `is_studying = False`, `reason = "no_cluster"` |
| Nhiều cluster kích thước tương đương | Chọn cluster có centroid **gần tâm quán nhất** làm dominant |
| Người đi lại liên tục | `spatial_std_m` cao → C4 không thỏa → `is_studying = False` |
| Ngồi trong quán liền kề (sai geofence) | C2 không thỏa → `is_studying = False` |
| Mất GPS giữa chừng > 10 phút | Khoảng trống > eps_temporal → ST-DBSCAN tạo 2 cluster riêng biệt, chọn cluster dài hơn |

---

## 7. Scoring Model

### 7.1 Bài toán cần giải

Behavior Score trả lời: *"Trong số những người track GPS tại quán này, bao nhiêu phần trăm có hành vi cho thấy họ đang học thực sự, và chất lượng học tập đó tốt đến mức nào?"*

**Quán điểm cao khi:**
- Tỷ lệ session `is_studying = True` cao (nhiều người học thực sự).
- Thời gian ổn định trung bình dài (người học ở lâu).
- Độ phân tán trong cluster thấp (môi trường yên tĩnh).
- Tỷ lệ rời sớm (< 30 phút) thấp.

Điểm nằm trong **[0.0, 10.0]** — scale 10 dễ đọc cho người dùng.

### 7.2 Features sử dụng

| Feature | Ký hiệu | Mô tả | Đơn vị | Nguồn |
|---|---|---|---|---|
| Tỷ lệ session học tập | `f1_study_rate` | % session có `is_studying=True` / tổng session | [0, 1] | Study Detection |
| Thời gian ổn định trung bình | `f2_avg_stable_dur` | mean(stable_duration_min) của session is_studying=True, chuẩn hóa với max=180 phút | [0, 1] | Study Detection |
| Độ ổn định không gian | `f3_spatial_stability` | `1 - normalize(mean(spatial_std_m), max=30m)` | [0, 1] | Study Detection |
| Tỷ lệ dữ liệu sạch | `f4_clean_data_rate` | % điểm GPS không bị đánh dấu nhiễu | [0, 1] | Noise Filter |
| Tỷ lệ rời sớm đảo ngược | `f5_retention` | `1 - dropoff_rate` (dropoff: session < 30 phút) | [0, 1] | Session metadata |
| Mật độ cluster | `f6_cluster_purity` | mean(dominant_cluster_pct) của session học | [0, 1] | Study Detection |
| Coverage ratio | `f7_coverage` | Tỷ lệ thời gian trong cluster / tổng thời gian session | [0, 1] | Study Detection |
| Volume signal | `f8_session_vol` | Dùng làm Bayesian confidence weight — không vào công thức trực tiếp | count | Backend |

### 7.3 Phương pháp tính điểm

**Lựa chọn: Weighted Scoring với Bayesian Average**

Đây là hybrid approach: công thức trọng số rõ ràng *(interpretable, dễ audit)* kết hợp Bayesian Average *(xử lý cold start và ngăn quán ít data bị inflate điểm)*.

**Lý do không dùng supervised ML ở v1.0:**
- Không có ground truth label — chưa ai đánh giá thủ công để tạo training set.
- Tập dữ liệu demo nhỏ → model sẽ overfit.
- Interpretability quan trọng hơn để team kiểm tra logic.

**Lý do chọn Bayesian Average thay vì EMA:**
- Bayesian Average có nền lý thuyết vững: nó chính xác là "blend về prior khi ít data, tin vào data khi nhiều data".
- Công thức tường minh, dễ giải thích cho mentor.
- EMA có thể gây bias với thứ tự session (session cuối có ảnh hưởng quá lớn nếu alpha lớn).

**Kế hoạch v2.0:** Khi có đủ dữ liệu (≥ 500 session, ≥ 10 quán), có thể thay scoring function bằng **Bayesian Ridge Regression** — học trọng số từ dữ liệu thực thay vì đặt tay, đồng thời cung cấp confidence interval cho điểm số.

### 7.4 Công thức / Mô tả model

**Bước 1: Tính raw_score từ weighted sum các features**

```
raw_score = w1×f1 + w2×f2 + w3×f3 + w4×f4 + w5×f5 + w6×f6 + w7×f7

Trọng số mặc định (tổng = 1.0):
w1 = 0.30   # study_rate       — quan trọng nhất: tỷ lệ người học thực sự
w2 = 0.20   # avg_stable_dur   — thời gian ổn định phản ánh chất lượng môi trường
w3 = 0.15   # spatial_stability — môi trường yên tĩnh → ít bị scatter
w4 = 0.10   # clean_data_rate  — chất lượng GPS tại quán (signal indoor)
w5 = 0.10   # retention        — tỷ lệ không rời sớm
w6 = 0.10   # cluster_purity   — mức độ tập trung trong cluster
w7 = 0.05   # coverage_ratio   — % thời gian ngồi yên / tổng session
```

`raw_score ∈ [0, 1]`

**Normalization các features liên tục:**

```python
f2 = min(avg_stable_dur_min  / 180.0, 1.0)   # 180 phút = 3 tiếng là max lý tưởng
f3 = 1 - min(mean_spatial_std_m / 30.0, 1.0) # 30m = eps DBSCAN là upper bound
f7 = coverage_ratio                           # đã ∈ [0, 1]
```

**Bước 2: Áp dụng Bayesian Average để tính cafe_score**

Bayesian Average blend giữa `raw_score` của quán và `prior` (điểm trung bình hệ thống) theo số lượng session:

```
S_cafe = (m × C + v × R) / (m + v)

Trong đó:
  v = total_study_sessions      # số session is_studying=True của quán
  R = raw_score × 10            # điểm hiện tại của quán (scale về [0,10])
  m = MIN_CONFIDENT_SESSIONS    # ngưỡng tin cậy (mặc định: 5)
  C = system_avg_score          # điểm trung bình toàn hệ thống (prior)
```

Ý nghĩa: khi `v → 0` thì `S_cafe → C` (pull về prior). Khi `v → ∞` thì `S_cafe → R` (tin vào data thực).

**Ví dụ minh họa:**
- Quán mới: 2 session, raw = 9.0 → S = (5×6.5 + 2×9.0) / 7 = **7.14** (bị kéo về prior, tránh inflate)
- Quán lâu: 30 session, raw = 9.0 → S = (5×6.5 + 30×9.0) / 35 = **8.66** (gần với data thực)

### 7.5 Cách train và lưu model (nếu dùng ML)

**v1.0:** Không có model file — toàn bộ là công thức toán học, cấu hình qua `config.py`.

**v2.0 (kế hoạch):**
- Dùng **Bayesian Ridge Regression** (`sklearn.linear_model.BayesianRidge`) để học trọng số từ data.
- Tập train: 500+ mock sessions với điểm được gán bằng công thức rule-based (bootstrap labels), sau đó fine-tune bằng implicit feedback (user quay lại quán = tín hiệu dương).
- Lưu model:

```python
import joblib
# Lưu pipeline gồm StandardScaler + BayesianRidge
joblib.dump({"scaler": scaler, "model": model}, "models/scoring_v2.joblib")

# Load khi khởi động (singleton):
artifacts = joblib.load("models/scoring_v2.joblib")
```

- Retrain offline hàng tuần hoặc khi có thêm ≥ 100 session mới.
- Thư mục:

```
scoring_engine/
    models/
        scoring_v2.joblib
    config.py          ← weights, thresholds — tất cả ở một chỗ
```

### 7.6 Đảm bảo miền giá trị output

```python
behavior_score = max(0.0, min(10.0, behavior_score))
behavior_score = round(behavior_score, 1)   # 1 chữ số thập phân, đủ cho UI
```

### 7.7 Xử lý trường hợp dữ liệu chưa đủ

```python
HAS_ENOUGH_DATA_THRESHOLD = 5  # tối thiểu 5 session is_studying=True

if studying_session_count < HAS_ENOUGH_DATA_THRESHOLD:
    has_enough_data = False
    # behavior_score vẫn được tính nội bộ (phục vụ debug và batch)
    # nhưng FE hiển thị "Chưa đủ dữ liệu" thay vì con số
```

---

## 8. Output Contract

### 8.1 Format output ở mức session

```python
# Trả về từ hàm score_session(payload)
{
    "session_id":   "uuid-string",
    "cafe_id":      1,

    # --- Noise Filter ---
    "total_gps_points":   120,
    "clean_gps_points":   108,
    "noise_point_count":  12,
    "clean_data_rate":    0.90,

    # --- Study Detection (ST-DBSCAN) ---
    "is_studying":                  True,
    "stable_duration_min":          87.0,
    "dominant_cluster_pct":         0.87,
    "centroid_distance_to_cafe_m":  18.3,
    "is_within_cafe_radius":        True,
    "spatial_std_m":                8.4,
    "coverage_ratio":               0.87,
    "cluster_count":                1,

    # --- Feature vector (cho logging/debug/v2 training) ---
    "features": {
        "f2_avg_stable_dur_norm": 0.483,
        "f3_spatial_stability":   0.72,
        "f4_clean_data_rate":     0.90,
        "f5_retention":           1.0,
        "f6_cluster_purity":      0.87,
        "f7_coverage_ratio":      0.87
    },

    # --- Meta ---
    "processing_time_ms": 38,
    "engine_version":      "2.0.0"
}
```

### 8.2 Format output ở mức quán

```python
# Trả về từ hàm update_cafe_score(cafe_id, session_result, cafe_history)
{
    "cafe_id":      1,
    "computed_at":  "2026-04-09T14:00:00Z",

    # --- Aggregate stats ---
    "total_sessions":           15,
    "studying_sessions":        11,
    "study_rate":               0.733,
    "avg_stable_duration_min":  74.5,
    "avg_spatial_std_m":        10.2,
    "dropoff_count":            2,
    "dropoff_rate":             0.133,

    # --- Bayesian Score ---
    "behavior_score":   7.8,
    "has_enough_data":  True,
    "bayesian_m":       5,       # MIN_CONFIDENT_SESSIONS dùng trong công thức
    "prior_score":      6.5,     # system_avg_score tại thời điểm tính

    # --- Meta ---
    "engine_version":  "2.0.0"
}
```

### 8.3 Cách trả kết quả về Backend

Module cung cấp **hai hàm public**. Backend tự ghi DB:

```python
from scoring_engine import score_session, update_cafe_score

# Khi session kết thúc:
session_result = score_session(payload)

# Cập nhật cafe score:
cafe_result = update_cafe_score(
    cafe_id       = payload["cafe"]["cafe_id"],
    session_result = session_result,
    cafe_history   = payload["cafe_history"]
)

# Backend persist:
db.session_results.insert(session_result)
db.cafe_scores.upsert(cafe_result)
```

---

## 9. Thư viện và công nghệ

| Thư viện | Mục đích sử dụng | Version dự kiến |
|---|---|---|
| `numpy` | Tính toán mảng, MAD, normalization | ≥ 1.24 |
| `pandas` | DataFrame manipulation, time series | ≥ 2.0 |
| `scikit-learn` | DBSCAN (custom metric), StandardScaler, BayesianRidge (v2) | ≥ 1.3 |
| `scipy` | Haversine distance, statistical functions | ≥ 1.11 |
| `python-dateutil` | Parse ISO 8601 timestamp robust | ≥ 2.8 |
| `joblib` | Lưu/load model (v2.0) | ≥ 1.3 |
| `pytest` | Unit test toàn pipeline | ≥ 7.0 |

**Không có dependency nặng** (TensorFlow, PyTorch) ở v1.0 — toàn bộ là classical statistics.

---

## 10. Kiến trúc module

```
scoring_engine/
├── __init__.py               # Export score_session, update_cafe_score
├── pipeline.py               # Orchestrator — gọi các bước theo thứ tự
├── noise_filter.py           # Bước 2: accuracy, speed, Hampel filter
├── st_dbscan.py              # Bước 3: ST-DBSCAN + stay-point detection
├── feature_extractor.py      # Bước 4: tính 7 features + normalization
├── scorer.py                 # Bước 5–6: session score + Bayesian cafe score
├── utils/
│   ├── haversine.py          # Haversine distance helper
│   └── validators.py         # Input validation & schema check
├── config.py                 # Tất cả constants/thresholds tập trung ở đây
├── models/                   # Placeholder cho v2.0 ML models
│   └── .gitkeep
└── tests/
    ├── test_noise_filter.py
    ├── test_st_dbscan.py
    ├── test_scorer.py
    └── fixtures/
        ├── session_studying_ideal.json
        ├── session_not_studying_short.json
        ├── session_noisy_gps.json
        ├── session_outside_cafe.json
        └── session_continuous_move.json
```

**`config.py` — tập trung tất cả hyperparameter:**

```python
# === Noise Filter ===
ACCURACY_THRESHOLD_M    = 50
SPEED_THRESHOLD_MS      = 8.33      # 30 km/h
MIN_TIME_DELTA_S        = 5
HAMPEL_WINDOW_K         = 2         # mỗi phía k điểm → cửa sổ 2k+1 = 5
HAMPEL_Z_THRESHOLD      = 3.0

# === ST-DBSCAN ===
EPS_SPATIAL_M           = 25
EPS_TEMPORAL_S          = 600       # 10 phút
DBSCAN_MIN_SAMPLES      = 3
RADIUS_BUFFER_M         = 20
MIN_STABLE_DURATION_MIN = 20
DOMINANT_CLUSTER_PCT    = 0.60
MAX_SPATIAL_STD_M       = 30

# === Scoring ===
WEIGHTS = {
    "study_rate":        0.30,
    "avg_stable_dur":    0.20,
    "spatial_stability": 0.15,
    "clean_data_rate":   0.10,
    "retention":         0.10,
    "cluster_purity":    0.10,
    "coverage_ratio":    0.05,
}
NORM_MAX_DURATION_MIN   = 180
NORM_MAX_SPATIAL_STD_M  = 30

# === Bayesian Average ===
MIN_CONFIDENT_SESSIONS  = 5         # m trong công thức Bayesian
HAS_ENOUGH_DATA_THRESH  = 5
DEFAULT_SYSTEM_AVG      = 5.0       # prior C khi chưa có system data
```

---

## 11. Kế hoạch kiểm thử

### 11.1 Test cases với mock data

| ID | Mô tả | Input | Kết quả mong đợi |
|---|---|---|---|
| TC01 | Happy path — học 90 phút | 90 điểm GPS, bán kính 15m, accuracy 10–20m | `is_studying=True`, `stable_dur≈90`, `score≥7.0` |
| TC02 | Session quá ngắn | 15 điểm (15 phút), GPS tốt | `is_studying=False`, `reason="too_short"` |
| TC03 | GPS nhiễu nặng | 60% điểm accuracy > 80m | `clean_rate < 0.5`, `has_enough_data=False` |
| TC04 | Ngồi ngoài quán | GPS tốt nhưng centroid cách tâm 200m | `is_within_cafe_radius=False`, `is_studying=False` |
| TC05 | Di chuyển liên tục | GPS thay đổi đều, không cluster | `is_studying=False`, `reason="no_cluster"` |
| TC06 | Quán chưa đủ dữ liệu | 3 session, 2 studying | `has_enough_data=False` |
| TC07 | Sáng học, chiều quay lại | 2 cụm cách nhau 4 giờ | ST-DBSCAN tạo 2 cluster riêng biệt |
| TC08 | Đi vệ sinh 5 phút | GPS lạc 50m trong 5 phút rồi quay lại | Khoảng trống < eps_temporal → vẫn 1 cluster |

### 11.2 Acceptance criteria

| Tiêu chí | Mục tiêu | Cách đo |
|---|---|---|
| Precision study detection | ≥ 80% | Test thủ công tại quán thật với 10 session có nhãn |
| Recall study detection | ≥ 75% | Không bỏ sót session học thật |
| Không crash với GPS xấu | 100% | Fuzz test với accuracy ngẫu nhiên 0–500m |
| Processing time / session (120 điểm) | < 500ms | Benchmark trên laptop thông thường |
| Score luôn trong [0, 10] | 100% | Unit test clamp logic |
| Bayesian Average khi v=0 → prior | 100% | Unit test công thức |

### 11.3 Edge cases cần test

```
- gps_points = []                          → mềm, không crash
- gps_points = [1 điểm duy nhất]          → is_studying = False
- Tất cả điểm cùng timestamp              → sort, xử lý được
- cafe.radius_meters = 0                  → buffer 20m vẫn hoạt động
- lat/lng ngoài phạm vi hợp lệ            → validate + reject
- accuracy = null toàn bộ                 → bỏ lớp A, vẫn chạy B + C
- timestamp sai format                    → raise ValueError rõ ràng
- cafe_history = null                     → chỉ trả session result
- Session dài 8 giờ (480 điểm)            → xử lý < 2s, không OOM
```

---

## 12. Câu hỏi mở / Cần quyết định

| # | Câu hỏi | Người cần trả lời | Trạng thái |
|---|---|---|---|
| 1 | Threshold `min_stable_duration = 20 phút` có quá cao không? Một số người học nhanh 15 phút rồi đi. | Cả nhóm | Chưa chốt |
| 2 | `cafe radius_meters` mặc định 50m có đủ cho quán lớn nhiều tầng không? Nên để 75–100m? | Backend(Anh Đức) | Chưa chốt |
| 3 | EMA alpha = 0.3 nghĩa là session mới chiếm 30% điểm. Có phù hợp không hay nên dùng simple average? | Team AI(Long/Tú) | Chưa chốt |
| 4 | Có cần endpoint `/api/scoring/recalculate-all` để chạy lại toàn bộ cafe score sau khi tune config không? | Backend(Anh Đức) | Chưa chốt |
| 5 | Mock data sẽ được generate theo phân phối nào? (Cần liên hệ với người làm mock data) | Team AI(Long/Tú) | Chưa chốt |
---

## 13. Ghi chú phiên bản

### v0.3 — Final Edition
- Nâng cấp toàn diện từ v1.0 dựa trên so sánh với 4 bản thiết kế song song của các AI khác.
- **Nâng cấp Noise Filter**: Chuyển từ Rolling Z-score → Hampel Identifier (MAD-based) — robust hơn với outlier chùm.
- **Nâng cấp Study Detection**: Chuyển từ DBSCAN thông thường → ST-DBSCAN — giải quyết bài toán "sáng học chiều quay lại" không bị gộp nhầm cluster.
- **Nâng cấp Scoring**: Chuyển từ EMA → Bayesian Average — nền lý thuyết vững, công thức tường minh, cold-start tốt hơn.
- Bổ sung feature `f7_coverage_ratio` và `f8_session_vol` (confidence weight).
- Bổ sung bảng so sánh lý do chọn thuật toán trong mỗi bước.
- Bổ sung lộ trình v2.0 với Bayesian Ridge Regression và Isolation Forest.
- Tổng hợp edge cases từ tất cả các bản.

### v0.2
- Hoàn thiện toàn bộ document từ khung v0.1.
- Thiết kế pipeline 6 bước đầy đủ.
- Chọn DBSCAN làm core algorithm cho study detection.
- Thiết kế weighted scoring + confidence scaling + EMA.
- Định nghĩa đầy đủ input/output contract, feature vector, test cases.
- Thêm phần kiến trúc module, lộ trình phát triển v2.0.

### v0.1
- Tạo khung template, chờ hoàn thiện nội dung.

### v1.0
- Phát hành phiên bản chính thức 1.0
