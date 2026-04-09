# Scoring Engine Design Document
## StudyCafe Analytics System

**Phiên bản:** v0.2  
**Ngày cập nhật:** 09/04/2026  

---

## 1. Mục tiêu module

Scoring Engine là module trung tâm chịu trách nhiệm **biến dữ liệu GPS thô thành chỉ số đánh giá chất lượng địa điểm học tập** một cách khách quan và tự động.

Module này giải quyết bài toán: *"Làm thế nào để biết một quán cafe có thực sự phù hợp để học tập hay không — không dựa vào ý kiến chủ quan, mà dựa vào hành vi thực tế của những người đã ngồi học tại đó?"*

Cụ thể, module thực hiện 3 nhiệm vụ chính:
1. **Lọc nhiễu GPS** — loại bỏ tín hiệu không đáng tin cậy trước khi phân tích.
2. **Phát hiện hành vi học tập** — dùng unsupervised ML để nhận diện session có dấu hiệu "ngồi yên, tập trung" khác với session "đến lấy đồ uống rồi đi".
3. **Tính điểm quán** — tổng hợp nhiều session thành một điểm behavior score đại diện cho mức độ phù hợp học tập của quán.

Module này là lý do hệ thống có giá trị hơn một ứng dụng check-in thông thường: điểm số phản ánh **trải nghiệm tập thể của nhiều người dùng thực tế**, không phải một người review.

---

## 2. Phạm vi và giới hạn

### 2.1 Trong phạm vi
- Nhận GPS logs của một session từ backend (qua function call).
- Lọc nhiễu GPS bằng kỹ thuật thống kê và vật lý.
- Phân tích không gian — thời gian để phát hiện hành vi học tập.
- Trích xuất feature vector mô tả hành vi của session.
- Tính điểm behavior score cho từng quán dựa trên tổng hợp nhiều session.
- Trả kết quả về backend ở dạng structured Python dict.
- Hỗ trợ cả real-time (tính ngay sau 1 session) và batch (tính lại toàn bộ).
- Ghi kết quả vào bảng `cafe_scores` thông qua backend.

### 2.2 Ngoài phạm vi
- Không trực tiếp ghi vào database — backend chịu trách nhiệm persist.
- Không xử lý authentication hay session management.
- Không phân tích nội dung hoạt động người dùng (chụp màn hình, loại ứng dụng đang dùng).
- Không dự đoán thời gian học tập tương lai.
- Không cá nhân hóa score theo từng user (điểm là của quán, không phải của user).
- Không ranking quán theo thẩm mỹ, giá cả hay menu.

### 2.3 Giả định
- GPS được gửi định kỳ mỗi **60 giây** trong suốt session.
- Accuracy GPS từ điện thoại thực tế dao động từ **5m đến 50m** trong điều kiện bình thường.
- Một session hợp lệ để tính điểm tối thiểu là **20 phút** (20 điểm GPS).
- Quán có tọa độ trung tâm và bán kính nhận diện (`radius_meters`) đã được hardcode sẵn.
- Dữ liệu mock và dữ liệu thật được xử lý bằng cùng pipeline.
- Trong giai đoạn demo, không có ground truth label — pipeline là **hoàn toàn unsupervised**.

---

## 3. Input Contract

### 3.1 Nguồn dữ liệu

Backend gọi module **sau khi session kết thúc** (`POST /api/session/end`). Backend truyền trực tiếp Python dict vào hàm `score_session()` — không có HTTP call nội bộ giữa backend và scoring engine.

Đây là kiến trúc **embedded module**: scoring engine chạy trong cùng process với backend (import như một Python package), không phải microservice riêng biệt. Quyết định này phù hợp với quy mô demo và giảm overhead tích hợp.

```
Backend process
    └── import scoring_engine
    └── result = scoring_engine.score_session(payload)
    └── db.save(result)
```

### 3.2 Format dữ liệu đầu vào
```python
{
    "session_id": "uuid-string",          # bắt buộc
    "device_id": "device-001",            # bắt buộc
    "cafe": {
        "cafe_id": 1,                     # bắt buộc
        "center_lat": 21.0285,            # bắt buộc
        "center_lng": 105.8542,           # bắt buộc
        "radius_meters": 50               # bắt buộc
    },
    "gps_points": [                       # bắt buộc, list có ít nhất 1 phần tử
        {
            "lat": 21.0285,               # bắt buộc
            "lng": 105.8542,              # bắt buộc
            "accuracy": 12.5,             # optional, đơn vị mét
            "timestamp": "2026-04-07T09:01:00Z"  # bắt buộc, ISO 8601
        }
    ]
}
```

### 3.3 Dữ liệu tham chiếu cần thêm

Ngoài GPS points, module cần thêm **lịch sử cafe_scores của quán** để cập nhật điểm tổng hợp. Backend cần truyền thêm:

```python
{
    # ... (như trên)
    "cafe_history": {
        "total_sessions_processed": 12,   # số session đã tính trước đó
        "current_score": 7.4,             # điểm hiện tại của quán, null nếu chưa có
        "has_enough_data": True           # đã có đủ dữ liệu chưa
    }
}
```

> Nếu `cafe_history` không được truyền vào, module vẫn chạy được nhưng chỉ trả kết quả ở mức session, không cập nhật được cafe score tổng hợp.

---

## 4. Pipeline tổng thể

```
Raw GPS Input (list of {lat, lng, accuracy, timestamp})
    │
    ▼
┌─────────────────────────────────────────┐
│  Bước 1: Validation & Preprocessing     │
│  - Parse timestamp, sort theo time      │
│  - Kiểm tra đủ điểm tối thiểu           │
│  - Tính time delta giữa các điểm        │
└─────────────────────┬───────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│  Bước 2: Noise Filter                   │
│  - Lọc theo accuracy threshold          │
│  - Lọc tốc độ di chuyển bất thường      │
│  - Lọc outlier bằng rolling z-score     │
│  - Đánh dấu is_noise = True             │
└─────────────────────┬───────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│  Bước 3: Study Detection                │
│  - DBSCAN clustering trên tọa độ        │
│  - Xác định dominant cluster            │
│  - Kiểm tra cluster có nằm trong        │
│    cafe radius không                    │
│  - Tính stable_duration                 │
└─────────────────────┬───────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│  Bước 4: Feature Extraction             │
│  - Tính 8 features mô tả hành vi        │
│  - Normalize về [0, 1]                  │
│  - Build feature vector                 │
└─────────────────────┬───────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│  Bước 5: Session Scoring                │
│  - Tính session_score từ weighted sum   │
│    các features                         │
│  - Gán nhãn is_studying True/False      │
└─────────────────────┬───────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│  Bước 6: Cafe Score Update              │
│  - Kết hợp session mới với lịch sử      │
│  - Exponential moving average update    │
│  - Kiểm tra has_enough_data threshold   │
└─────────────────────┬───────────────────┘
                      │
                      ▼
              Output Score Dict
```

---

## 5. Noise Filter

### 5.1 Vấn đề cần giải quyết

GPS trên smartphone có các loại nhiễu phổ biến sau:
- **Accuracy spike**: máy báo vị trí nhưng accuracy = 200m → vô nghĩa.
- **GPS jump**: tọa độ nhảy đột ngột 500m rồi quay lại → do multipath reflection trong toà nhà.
- **Stale GPS**: timestamp trùng hoặc rất gần nhau do cache → duplicate data.
- **Drift drift trong nhà**: tọa độ trôi dần 20–30m dù người ngồi yên → nhiễu từ tường/trần.
- **Initial lock noise**: 2–3 điểm GPS đầu tiên sau khi mở app thường kém chính xác.

### 5.2 Thuật toán / Phương pháp chọn

Sử dụng **3 lớp lọc tuần tự**, từ đơn giản đến phức tạp:

**Lớp 1 — Accuracy threshold filter**  
Lọc trực tiếp theo field `accuracy` từ GPS API. Điểm có accuracy > 50m bị loại.  
Lý do chọn: đơn giản, chi phí O(n), loại được phần lớn nhiễu nặng.

**Lớp 2 — Speed filter (vật lý)**  
Tính tốc độ di chuyển giữa hai điểm liên tiếp bằng công thức Haversine:

```
speed = haversine(p[i], p[i+1]) / time_delta[i]
```

Điểm có speed > ngưỡng (xem 5.3) bị đánh dấu là nhiễu.  
Lý do chọn: không thể đi bộ 200m/s trong quán cafe — vi phạm vật lý là dấu hiệu rõ ràng của GPS glitch.

**Lớp 3 — Rolling Z-score filter (thống kê)**  
Tính z-score của lat và lng trong cửa sổ trượt 5 điểm:

```
z = (x - rolling_mean) / rolling_std
```

Điểm có |z| > ngưỡng bị đánh dấu là outlier.  
Lý do chọn: bắt được drift cục bộ mà speed filter bỏ qua — khi GPS trôi từ từ, speed hợp lý nhưng vị trí lệch dần khỏi centroid.

### 5.3 Tiêu chí đánh dấu là nhiễu

| Điều kiện | Ngưỡng | Lý do |
|---|---|---|
| `accuracy > 50` | 50m | GPS trên 50m không đủ độ tin cậy trong không gian quán |
| `speed > 8.33 m/s` | 30 km/h | Tốc độ tối đa có thể chấp nhận trong khu vực đô thị |
| `|z_lat| > 3.0` hoặc `|z_lng| > 3.0` | z = 3 | Ngưỡng thống kê chuẩn cho outlier |
| `time_delta < 5s` | 5 giây | Điểm quá gần nhau — likely duplicate/cache |

### 5.4 Output của bước này
```python
[
    {
        "lat": 21.0285,
        "lng": 105.8542,
        "accuracy": 12.5,
        "timestamp": "2026-04-07T09:01:00Z",
        "is_noise": False,
        "noise_reason": None          # hoặc "accuracy", "speed", "zscore", "duplicate"
    },
    ...
]
```

Điểm noise không bị xóa khỏi list mà chỉ được đánh dấu `is_noise = True`, giữ lại để audit log và debug.

### 5.5 Edge cases cần xử lý

- **Tất cả điểm đều là noise** → trả về `{"is_studying": False, "reason": "all_noise"}`, không crash.
- **Dưới 5 điểm sau lọc** → không đủ để phân tích, trả về `has_enough_data: False`.
- **accuracy = null** (GPS API không trả về) → bỏ qua lớp 1, vẫn chạy lớp 2 và 3.
- **Timestamp không tăng đơn điệu** → sort lại trước khi tính speed.

---

## 6. Study Detection

### 6.1 Định nghĩa "đang học" trong hệ thống này

**Ngôn ngữ tự nhiên:**  
Một session được coi là "đang học" nếu người dùng **ở yên một chỗ trong thời gian dài** tại **địa điểm gần với quán được gán**. Session chạy qua rồi về, hoặc ngồi nhưng liên tục di chuyển, không được tính là học.

**Chuyển thành điều kiện toán học:**

```
Điều kiện 1: Tồn tại ít nhất 1 spatial cluster chứa ≥ 60% số điểm GPS sạch.

Điều kiện 2: Centroid của dominant cluster nằm trong vòng tròn (center_lat, center_lng, radius_meters) của quán.

Điều kiện 3: Thời gian liên tục người dùng ở trong cluster (stable_duration) ≥ 20 phút.

Điều kiện 4: Độ phân tán trong cluster (movement_std) ≤ 30m (phù hợp với GPS drift trong nhà).
```

**is_studying = True khi tất cả 4 điều kiện đều thỏa mãn.**

### 6.2 Thuật toán / Phương pháp chọn

**DBSCAN (Density-Based Spatial Clustering of Applications with Noise)**

Lý do chọn DBSCAN thay vì K-Means hay threshold đơn giản:
- Không cần biết trước số cluster — phù hợp vì người dùng có thể di chuyển giữa 2–3 khu vực trong quán.
- Tự động nhận diện outlier (nhãn -1) — đây chính xác là điểm GPS "lang thang" cần tách khỏi cluster học tập.
- Hoạt động tốt với dữ liệu có mật độ không đều — các cụm GPS thực tế không tròn đều.
- Chi phí tính toán thấp — tập dữ liệu demo chỉ ~120 điểm/session.

**Cách áp dụng Haversine Distance trong DBSCAN:**  
DBSCAN mặc định dùng Euclidean distance, nhưng tọa độ GPS cần Haversine. Dùng `sklearn` với `metric='haversine'` và input là mảng `[lat_rad, lng_rad]`.

```python
from sklearn.cluster import DBSCAN
import numpy as np

coords_rad = np.radians(clean_points[['lat', 'lng']].values)
db = DBSCAN(
    eps=eps_rad,          # eps tính bằng radian (xem 6.3)
    min_samples=min_pts,
    algorithm='ball_tree',
    metric='haversine'
).fit(coords_rad)
```

### 6.3 Parameters và lý do chọn

| Parameter | Giá trị | Giải thích |
|---|---|---|
| `eps` | 30m → 0.000267 radian | Bán kính cluster. 30m = GPS drift tối đa trong nhà. Chuyển sang radian: eps_m / 6371000 |
| `min_samples` | 3 | Tối thiểu 3 điểm GPS để tạo cluster = 3 phút. Tránh noise bị cluster |
| `accuracy_threshold` | 50m | Chỉ feed điểm sạch vào DBSCAN |
| `min_stable_duration` | 20 phút | Số phút tối thiểu trong dominant cluster |
| `dominant_cluster_pct` | 60% | Cluster phải chứa ít nhất 60% điểm sạch |

**Lý do chọn eps = 30m:**  
Thực nghiệm trên GPS indoor cho thấy drift thường trong khoảng 10–25m. 30m là buffer đủ an toàn mà không quá rộng để merge các khu vực khác nhau trong quán.

### 6.4 Output của bước này
```python
{
    "cluster_labels": [0, 0, -1, 0, 1, 0, ...],  # nhãn DBSCAN cho mỗi điểm sạch
    "dominant_cluster_id": 0,
    "dominant_cluster_point_count": 85,
    "dominant_cluster_pct": 0.87,
    "dominant_cluster_centroid": {
        "lat": 21.02851,
        "lng": 105.85423
    },
    "centroid_distance_to_cafe_m": 18.3,      # khoảng cách Haversine đến center quán
    "is_within_cafe_radius": True,
    "stable_duration_min": 87.0,
    "movement_std_m": 8.4,                    # std độ lệch tọa độ trong cluster, đơn vị mét
    "is_studying": True
}
```

### 6.5 Edge cases cần xử lý

- **Session quá ngắn (< 20 phút)**: `is_studying = False`, `reason = "too_short"`. Không cố cluster.
- **GPS drift liên tục — không có cluster nào**: tất cả điểm là noise DBSCAN (label = -1). `is_studying = False`, `reason = "no_cluster"`.
- **Nhiều cluster có kích thước tương đương**: chọn cluster gần tâm quán nhất làm dominant.
- **Người đi lại liên tục trong quán**: `movement_std_m` cao → điều kiện 4 không thỏa → `is_studying = False`.
- **Session tại quán khác nhưng sát nhau**: `is_within_cafe_radius = False` → không tính cho quán này.

---

## 7. Scoring Model

### 7.1 Bài toán cần giải

Điểm hành vi (`behavior_score`) của một quán cafe trả lời câu hỏi:  
**"Trong số những người đã track GPS tại quán này, bao nhiêu phần trăm có hành vi thực sự cho thấy họ đang học, và chất lượng hành vi đó tốt đến mức nào?"**

Quán được điểm cao khi:
- Tỷ lệ session có `is_studying = True` cao.
- Những session học có thời gian ổn định dài.
- Người dùng ít di chuyển trong quán (môi trường yên tĩnh → ít bị scatter).
- Tỷ lệ rời sớm (< 30 phút) thấp.

Điểm nằm trong khoảng **[0.0, 10.0]** — scale 10 cho dễ đọc.

### 7.2 Features sử dụng

| Feature | Ký hiệu | Mô tả | Đơn vị | Nguồn |
|---|---|---|---|---|
| Tỷ lệ session học tập | `f1_study_rate` | % session có is_studying=True / tổng session | [0,1] | Study Detection |
| Thời gian ổn định trung bình | `f2_avg_stable_dur` | mean(stable_duration_min) của session is_studying=True | phút → normalize | Study Detection |
| Độ ổn định vị trí | `f3_movement_stability` | 1 - normalize(mean(movement_std_m)) | [0,1] | Study Detection |
| Tỷ lệ dữ liệu sạch | `f4_clean_data_rate` | % điểm GPS không bị đánh dấu noise | [0,1] | Noise Filter |
| Tỷ lệ rời sớm | `f5_dropoff_rate` | % session < 30 phút | [0,1] | Session metadata |
| Độ tập trung cluster | `f6_cluster_purity` | mean(dominant_cluster_pct) của session học | [0,1] | Study Detection |
| Thời gian phiên dài nhất | `f7_max_duration` | max(stable_duration_min) — tín hiệu về khả năng "học được lâu" | phút → normalize | Study Detection |
| Số session hợp lệ | `f8_session_volume` | Dùng làm confidence weight, không vào công thức trực tiếp | count | Backend |

### 7.3 Phương pháp tính điểm

**Lựa chọn: Weighted Scoring với Confidence Decay**

Đây là hybrid approach: công thức trọng số rõ ràng (interpretable) kết hợp với confidence scaling dựa trên số lượng dữ liệu (adaptive).

Lý do **không dùng supervised ML** trong giai đoạn này:
- Không có ground truth label (chưa ai đánh giá thủ công quán nào "tốt hơn" quán nào để train).
- Tập dữ liệu demo nhỏ — model ML sẽ overfit.

Lý do **không dùng thuần rule-based**:
- Weighted scoring cho phép tuning trọng số khi có thêm feedback thực tế.
- Confidence decay xử lý được bài toán "quán mới chỉ có 2 session — điểm không đáng tin".

**Mở rộng tương lai:** Khi có đủ dữ liệu (≥ 100 session trên ≥ 5 quán), có thể thay thế hoặc bổ sung bằng **Isolation Forest** để phát hiện session bất thường, hoặc **Light Gradient Boosting** nếu có pseudo-labels.

### 7.4 Công thức / Mô tả model

**Bước 1: Tính raw_score từ weighted sum**

```
raw_score = w1*f1 + w2*f2 + w3*f3 + w4*f4 + w5*(1-f5) + w6*f6 + w7*f7

Với trọng số mặc định:
w1 = 0.30   # study_rate — quan trọng nhất
w2 = 0.20   # avg_stable_duration
w3 = 0.15   # movement_stability
w4 = 0.10   # clean_data_rate
w5 = 0.10   # (1-dropoff_rate)
w6 = 0.10   # cluster_purity
w7 = 0.05   # max_duration
```

> Tổng trọng số = 1.0. raw_score ∈ [0, 1].

**Bước 2: Áp dụng Confidence Scaling**

Khi số session ít, điểm chưa đáng tin. Áp dụng confidence factor:

```python
CONFIDENCE_MIN_SESSIONS = 5    # dưới 5 session → confidence thấp
CONFIDENCE_FULL_SESSIONS = 20  # từ 20 session trở lên → full confidence

confidence = min(total_sessions / CONFIDENCE_FULL_SESSIONS, 1.0)

# Blend giữa prior (5.0) và raw_score khi ít dữ liệu
PRIOR_SCORE = 5.0  # điểm trung bình khi chưa biết gì
behavior_score = confidence * (raw_score * 10) + (1 - confidence) * PRIOR_SCORE
```

**Bước 3: Exponential Moving Average khi cập nhật quán**

Khi có session mới, không tính lại từ đầu mà dùng EMA:

```python
ALPHA = 0.3   # trọng số session mới
new_cafe_score = ALPHA * session_contribution + (1 - ALPHA) * old_cafe_score
```

Lý do dùng EMA: quán có thể thay đổi theo thời gian (thay chủ, renovate) — session gần đây nên có trọng số cao hơn.

**Normalization các features:**

```python
# f2: normalize avg_stable_dur về [0,1] với max = 180 phút
f2 = min(avg_stable_dur_min / 180.0, 1.0)

# f3: normalize movement_std với max = 30m (= eps của DBSCAN)
f3 = 1 - min(mean_movement_std_m / 30.0, 1.0)

# f7: normalize max_duration với max = 240 phút
f7 = min(max_stable_dur_min / 240.0, 1.0)
```

### 7.5 Cách train và lưu model (nếu dùng ML)

Ở v1.0, không có model ML cần train — toàn bộ là công thức toán học.

**Kế hoạch cho v2.0 (sau demo):**

Nếu thu thập được đủ dữ liệu thực tế:
- Dùng **Isolation Forest** (`sklearn.ensemble.IsolationForest`) để phát hiện session bất thường tự động thay cho rule-based noise detection.
- Train trên feature vector [f1..f7] của các session.
- Lưu model dạng `.joblib`:

```python
import joblib
joblib.dump(model, "models/isolation_forest_v1.joblib")

# Backend load:
model = joblib.load("models/isolation_forest_v1.joblib")
```

- Retrain định kỳ mỗi 2 tuần hoặc khi có thêm ≥ 50 session mới.

**Thư mục lưu model:**
```
scoring_engine/
    models/
        isolation_forest_v1.joblib
        scaler_v1.joblib        # StandardScaler để normalize features
        weights_config.json     # trọng số w1..w7, có thể tune runtime
```

### 7.6 Đảm bảo miền giá trị output

```python
# behavior_score luôn nằm trong [0.0, 10.0]
behavior_score = max(0.0, min(10.0, behavior_score))
behavior_score = round(behavior_score, 2)
```

### 7.7 Xử lý trường hợp dữ liệu chưa đủ

```python
HAS_ENOUGH_DATA_THRESHOLD = 5  # tối thiểu 5 session is_studying=True

if studying_session_count < HAS_ENOUGH_DATA_THRESHOLD:
    has_enough_data = False
    # behavior_score vẫn được tính nhưng FE sẽ hiển thị "Chưa đủ dữ liệu"
    # thay vì hiển thị con số
else:
    has_enough_data = True
```

---

## 8. Output Contract

### 8.1 Format output ở mức session

```python
# Kết quả sau khi xử lý 1 session — trả về từ score_session()
{
    "session_id": "uuid-string",
    "cafe_id": 1,

    # --- Noise Filter results ---
    "total_gps_points": 120,
    "clean_gps_points": 108,
    "noise_point_count": 12,
    "clean_data_rate": 0.90,

    # --- Study Detection results ---
    "is_studying": True,
    "stable_duration_min": 87.0,
    "dominant_cluster_pct": 0.87,
    "centroid_distance_to_cafe_m": 18.3,
    "is_within_cafe_radius": True,
    "movement_std_m": 8.4,
    "cluster_count": 1,

    # --- Feature vector (cho logging/debug) ---
    "features": {
        "f1_study_rate": None,          # f1 là mức quán, không có ở mức session
        "f2_stable_dur_norm": 0.483,
        "f3_movement_stability": 0.72,
        "f4_clean_data_rate": 0.90,
        "f5_dropoff": False,
        "f6_cluster_purity": 0.87,
        "f7_max_dur_norm": 0.363
    },

    # --- Meta ---
    "processing_time_ms": 42,
    "engine_version": "1.0.0"
}
```

### 8.2 Format output ở mức quán (dùng cho scoring + export)

```python
# Kết quả tổng hợp theo cafe_id — trả về từ update_cafe_score()
{
    "cafe_id": 1,
    "computed_at": "2026-04-09T14:00:00Z",

    # --- Aggregate stats ---
    "total_sessions": 15,
    "studying_sessions": 11,
    "study_rate": 0.733,
    "avg_stable_duration_min": 74.5,
    "avg_movement_std_m": 10.2,
    "dropoff_count": 2,
    "dropoff_rate": 0.133,

    # --- Score ---
    "behavior_score": 7.84,
    "has_enough_data": True,
    "confidence": 0.75,              # confidence factor (0..1)

    # --- Meta ---
    "engine_version": "1.0.0"
}
```

### 8.3 Cách trả kết quả về Backend

Module trả kết quả thông qua **return value của function** — backend tự quyết định có ghi DB không.

```python
# Hai hàm public của module:

def score_session(payload: dict) -> dict:
    """Xử lý 1 session, trả session-level result."""
    ...

def update_cafe_score(cafe_id: int, session_result: dict, cafe_history: dict) -> dict:
    """Cập nhật cafe score dựa trên session mới, trả cafe-level result."""
    ...
```

Backend sử dụng:
```python
from scoring_engine import score_session, update_cafe_score

session_result = score_session(payload)
cafe_result = update_cafe_score(
    cafe_id=payload["cafe"]["cafe_id"],
    session_result=session_result,
    cafe_history=payload["cafe_history"]
)

# Backend tự ghi vào DB
db.session_results.insert(session_result)
db.cafe_scores.upsert(cafe_result)
```

---

## 9. Thư viện và công nghệ

| Thư viện | Mục đích sử dụng | Version dự kiến |
|---|---|---|
| `numpy` | Tính toán mảng số, rolling statistics | ≥ 1.24 |
| `pandas` | DataFrame manipulation, time series handling | ≥ 2.0 |
| `scikit-learn` | DBSCAN clustering, StandardScaler, Isolation Forest (v2) | ≥ 1.3 |
| `scipy` | Haversine distance, statistical functions | ≥ 1.11 |
| `joblib` | Lưu/load model (dùng ở v2.0) | ≥ 1.3 |
| `python-dateutil` | Parse ISO 8601 timestamp robust | ≥ 2.8 |
| `pytest` | Unit test pipeline | ≥ 7.0 |

**Không có dependency nặng** như TensorFlow hay PyTorch ở v1.0 — tất cả là classical ML/statistics.

---

## 10. Kiến trúc module

```
scoring_engine/
├── __init__.py               # Export score_session, update_cafe_score
├── pipeline.py               # Orchestrator — gọi các bước theo thứ tự
├── noise_filter.py           # Bước 2: accuracy, speed, z-score filter
├── study_detector.py         # Bước 3: DBSCAN + study detection logic
├── feature_extractor.py      # Bước 4: tính 7 features
├── scorer.py                 # Bước 5–6: session score + cafe score update
├── utils/
│   ├── haversine.py          # Haversine distance helper
│   ├── normalizer.py         # Feature normalization helpers
│   └── validators.py         # Input validation
├── config.py                 # Tất cả constants/thresholds ở một chỗ
├── models/                   # Placeholder cho v2.0 ML models
│   └── .gitkeep
└── tests/
    ├── test_noise_filter.py
    ├── test_study_detector.py
    ├── test_scorer.py
    └── fixtures/
        ├── mock_session_studying.json
        ├── mock_session_not_studying.json
        └── mock_session_noisy.json
```

**`config.py`** tập trung tất cả hyperparameter để dễ tune:

```python
# config.py
ACCURACY_THRESHOLD_M = 50
SPEED_THRESHOLD_MS = 8.33        # 30 km/h
ZSCORE_THRESHOLD = 3.0
MIN_TIME_DELTA_S = 5

DBSCAN_EPS_M = 30
DBSCAN_MIN_SAMPLES = 3
MIN_STABLE_DURATION_MIN = 20
DOMINANT_CLUSTER_PCT_THRESHOLD = 0.60
MAX_MOVEMENT_STD_M = 30

WEIGHTS = {
    "study_rate": 0.30,
    "avg_stable_dur": 0.20,
    "movement_stability": 0.15,
    "clean_data_rate": 0.10,
    "dropoff_penalty": 0.10,
    "cluster_purity": 0.10,
    "max_duration": 0.05,
}

CONFIDENCE_FULL_SESSIONS = 20
HAS_ENOUGH_DATA_THRESHOLD = 5
PRIOR_SCORE = 5.0
EMA_ALPHA = 0.3
```

---

## 11. Kế hoạch kiểm thử

### 11.1 Test với mock data

**Test case 1 — Happy path: session học tập điển hình**
- Input: 90 điểm GPS tập trung trong bán kính 20m, accuracy 10–20m, duration 90 phút.
- Mong đợi: `is_studying = True`, `stable_duration_min ≈ 90`, `behavior_score > 7.0`.

**Test case 2 — Session quá ngắn**
- Input: 15 điểm GPS (15 phút), tập trung tốt.
- Mong đợi: `is_studying = False`, `reason = "too_short"`.

**Test case 3 — GPS nhiều nhiễu**
- Input: 60% điểm có accuracy > 80m, các điểm còn lại tốt.
- Mong đợi: `clean_data_rate < 0.5`, `has_enough_data = False` hoặc `is_studying = False`.

**Test case 4 — Session qua quán khác**
- Input: GPS tốt nhưng centroid cách tâm quán 200m (ngoài radius).
- Mong đợi: `is_within_cafe_radius = False`, `is_studying = False`.

**Test case 5 — Di chuyển liên tục**
- Input: GPS thay đổi liên tục, không có cluster nào > 40%.
- Mong đợi: `is_studying = False`, `reason = "no_dominant_cluster"`.

**Test case 6 — Cafe chưa đủ dữ liệu**
- Input: 3 session, 2 có `is_studying = True`.
- Mong đợi: `has_enough_data = False`, `behavior_score` được tính nhưng FE không hiển thị.

### 11.2 Acceptance criteria

| Tiêu chí | Mục tiêu | Cách đo |
|---|---|---|
| Precision study detection | ≥ 80% | Test thủ công tại quán thật với 10 session có nhãn |
| Recall study detection | ≥ 75% | Không bỏ sót session học thật |
| Không crash với GPS xấu | 100% | Fuzz test với accuracy ngẫu nhiên 0–500m |
| Processing time / session | < 500ms | Benchmark trên 120 điểm GPS |
| Score trong miền [0, 10] | 100% | Unit test clamp logic |

### 11.3 Edge cases cần test

```
- List gps_points rỗng []
- List chỉ có 1 điểm
- Tất cả điểm có cùng timestamp
- cafe radius_meters = 0
- lat/lng ngoài phạm vi hợp lệ (-90..90, -180..180)
- accuracy = null / không có trường accuracy
- timestamp không hợp lệ (sai format)
- cafe_history = null (quán mới chưa có lịch sử)
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

### v0.2
- Hoàn thiện toàn bộ document từ khung v0.1.
- Thiết kế pipeline 6 bước đầy đủ.
- Chọn DBSCAN làm core algorithm cho study detection.
- Thiết kế weighted scoring + confidence scaling + EMA.
- Định nghĩa đầy đủ input/output contract, feature vector, test cases.
- Thêm phần kiến trúc module, lộ trình phát triển v2.0.

### v0.1
- Tạo khung template, chờ hoàn thiện nội dung.
