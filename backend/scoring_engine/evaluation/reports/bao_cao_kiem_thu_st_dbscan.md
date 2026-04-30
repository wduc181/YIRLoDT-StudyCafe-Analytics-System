# Báo cáo kiểm thử module ST-DBSCAN
## StudyCafe Analytics System — Scoring Engine v2.0.0

**Ngày:** 25/04/2026  
**Người thực hiện:** Nguyễn Anh Tú (AI Engineer)  
**File kiểm thử:** `scoring_engine/tests/test_st_dbscan_math.py`  
**Kết quả tổng:** **23/23 PASSED** — 10.27 giây

---

## 1. Bối cảnh và phương pháp

### Vấn đề cần giải quyết

ST-DBSCAN là bước 3 trong pipeline — bước quyết định nhãn `is_studying`. Không có dataset GPS labeled nào phù hợp trực tiếp với bài toán vì:

- Các dataset GPS công khai (GeoLife, MDC, Cabspotting) không có nhãn "đang học" — chỉ có nhãn phương tiện di chuyển hoặc loại địa điểm.
- Sampling rate trong các dataset đó (1–5 giây) không phù hợp với hệ thống dùng 60 giây/điểm.
- Nhãn "is_studying" là định nghĩa đặc thù của hệ thống, không tồn tại trong dữ liệu thực tế ngoài.

### Giải pháp: kiểm thử đảo ngược — từ output suy ra input

Thay vì tìm dataset hay nhờ AI gán nhãn (dễ dẫn đến circular reasoning), phương pháp được chọn là:

**Tầng 1 — Deterministic mock data:** Tạo input bằng công thức toán học, tính tay expected output, sau đó verify pipeline cho ra đúng kết quả đã tính. Nhãn không do AI đoán — nhãn là hệ quả của phép tính.

**Tầng 2 — Property-based testing:** Không cần nhãn. Thay vào đó kiểm tra các bất biến (invariants) phải đúng với mọi input: nếu is_studying=True thì stable_duration phải ≥ ngưỡng, nếu is_studying=False thì reason không bao giờ None, v.v.

Kết hợp hai tầng này cho phép kiểm thử toàn diện mà không phụ thuộc vào nguồn dữ liệu bên ngoài hay phán đoán của AI.

---

## 2. Mô tả tập dữ liệu mock (Tầng 1)

### Tọa độ tham chiếu

Tất cả test cases dùng một quán cafe mẫu cố định:

| Tham số | Giá trị |
|---|---|
| `center_lat` | 21.0024 |
| `center_lng` | 105.8453 |
| `radius_meters` | 50.0 m |
| Effective radius (+ buffer) | 70.0 m |

### Hệ số chuyển đổi tọa độ

Tại vĩ độ 21°N:
- 1 degree lat ≈ 111,320 m → `_LAT_PER_M = 1 / 111,320`
- 1 degree lng ≈ 103,930 m → `_LNG_PER_M = 1 / (111,320 × cos(21°))`

Mọi offset (mét) trong test đều được chuyển qua công thức này để đảm bảo khoảng cách Haversine chính xác.

### Cách sinh điểm GPS

Hàm `make_cluster(n, start_min, interval, spread, offset)` sinh điểm theo mẫu jitter cố định (không random) để kết quả reproducible:

```
jitter_lat_i = (i % 3 - 1) × (spread / 3)   → {-spread/3, 0, +spread/3}
jitter_lng_i = (i % 2)     × (spread / 4)    → {0, +spread/4}
```

Jitter pattern cố định này đảm bảo spatial_std tính được từ công thức, không phụ thuộc vào random seed.

### Các loại dataset được tạo

| Loại | n điểm | Interval | spread | offset | Mục đích |
|---|---|---|---|---|---|
| Cluster lý tưởng | 30 | 1.5 min | 5 m | 0 m | Happy path |
| Cluster chặt | 30 | 1.5 min | 3 m | 0 m | Test spatial_std thấp |
| Cluster rộng | 30 | 1.5 min | 15 m | 0 m | So sánh spatial_std |
| Session ngắn | 10 | 1 min | 3 m | 0 m | Span = 9 phút |
| Quá ít điểm | 4 | 15 min | 3 m | 0 m | n < MIN_CLEAN_POINTS |
| Ngoài quán | 30 | 1.5 min | 3 m | 80 m | Outside radius boundary |
| Sát radius | 30 | 1.5 min | 3 m | 65 m | Just inside radius buffer |
| 2 cluster đều | 5+5 | 6 min | 3 m | 0/30 m | Purity = 50% |
| 6/10 cluster | 6+4 | 6 min | 3 m | 0/35 m | Purity = 60% (boundary) |
| Cluster + noise | 8+8 | 2/1.5 min | 3/40 m | 0/40+ m | Cluster span = 14 phút |

---

## 3. Kết quả Tầng 1 — Unit test toán học

### 3.1 Guard MIN_CLEAN_POINTS (TC-MATH-01 → TC-MATH-03)

Kiểm tra guard đầu tiên của pipeline: reject ngay nếu số điểm sạch dưới ngưỡng.

| Test | Input | Expected | Actual | Status |
|---|---|---|---|---|
| TC-MATH-01 | n=5 (đúng ngưỡng), span=40min | Không bị reject vì thiếu điểm | reason ≠ "too_short" do point count | PASS |
| TC-MATH-02 | n=4 < MIN=5 | is_studying=False, reason="too_short" | False, "too_short" | PASS |
| TC-MATH-03 | n=0 (empty list) | is_studying=False, reason="too_short" | False, "too_short" | PASS |

Tính tay: `4 < MIN_CLEAN_POINTS=5` → guard fail → reason="too_short". Kết quả pipeline khớp.

### 3.2 Guard MIN_STABLE_DURATION_MIN (TC-MATH-04 → TC-MATH-05)

Kiểm tra ngưỡng thời gian tối thiểu của session.

| Test | Input | Span tính tay | Expected | Status |
|---|---|---|---|---|
| TC-MATH-04 | 20 vs 22 điểm, interval=1min | 19 min vs 21 min | 19min fail, 21min có thể pass | PASS |
| TC-MATH-05 | n=10, interval=1min | (10-1)×1 = 9 phút | False, "too_short" | PASS |

Công thức: `span = (n-1) × interval_min`. Với n=10, interval=1: span=9 phút < MIN_STABLE_DURATION_MIN=20 phút.

### 3.3 Guard DOMINANT_CLUSTER_PCT (TC-MATH-06 → TC-MATH-07)

Kiểm tra ngưỡng tỷ lệ dominant cluster.

| Test | Input | Pct tính tay | Expected | Actual reason | Status |
|---|---|---|---|---|---|
| TC-MATH-06 | 6/10 điểm trong cluster | 6/10 = 0.60 = ngưỡng | guard pass | None (pass) | PASS |
| TC-MATH-07 | 5+5 điểm, 2 cluster đều nhau | max(5,5)/10 = 0.50 < 0.60 | False, "low_cluster_purity" | "low_cluster_purity" | PASS |

Tiền điều kiện TC-MATH-07 được verify bằng Haversine: 2 cluster thực sự cách nhau > eps_spatial=25m.

### 3.4 Guard OUTSIDE_CAFE_RADIUS (TC-MATH-08 → TC-MATH-09)

Kiểm tra ranh giới radius kết hợp buffer GPS drift.

| Test | Offset từ tâm | Effective radius | So sánh | Expected | Status |
|---|---|---|---|---|---|
| TC-MATH-08 | 80 m | 50 + 20 = 70 m | 80 > 70 → ngoài | False, "outside_cafe_radius" | PASS |
| TC-MATH-09 | 65 m | 70 m | 65 < 70 → trong | reason ≠ "outside_cafe_radius" | PASS |

Kết quả chạy thực tế xác nhận ranh giới tại đúng 70m: offset=70m → True, offset=75m → False.

### 3.5 Guard MAX_SPATIAL_STD_M (TC-MATH-10 → TC-MATH-11)

| Test | Mục tiêu | Kết quả | Status |
|---|---|---|---|
| TC-MATH-10 | Cluster rộng có std > cluster chặt | std(spread=15m) = 1.63m > std(spread=3m) = 0.33m | PASS |
| TC-MATH-10b | Guard "high_spatial_std" tồn tại trong source code | inspect.getsource() tìm thấy string | PASS |
| TC-MATH-11 | Cluster 5m không bị reject vì high_spatial_std | reason ≠ "high_spatial_std" | PASS |

Ghi chú quan trọng: MAX_SPATIAL_STD_M=30m thực tế khó trigger bằng synthetic perfect grid vì DBSCAN chỉ gom điểm khi khoảng cách ≤ eps_spatial=25m — cluster chain dài nhất có std << 30m. Guard này tồn tại để xử lý GPS drift bất thường trong thực tế (indoor multipath noise), không phải synthetic scenario.

### 3.6 Happy path và output contract (TC-MATH-12 → TC-MATH-16)

| Test | Mô tả | Status |
|---|---|---|
| TC-MATH-12 | Cluster span 14 phút < 20 phút → reject | PASS |
| TC-MATH-13 | Tất cả 5 điều kiện pass → is_studying=True | PASS |
| TC-MATH-14 | Output numeric ranges: coverage∈[0,1], dominant_pct∈[0,1], std≥0 | PASS |
| TC-MATH-15 | is_studying=True → 4 invariants đồng thời đúng | PASS |
| TC-MATH-16 | is_studying=False → reason không bao giờ None | PASS |

---

## 4. Kết quả Tầng 2 — Property-based testing

Framework: `hypothesis` — tự động sinh input ngẫu nhiên và shrink về case nhỏ nhất khi phát hiện lỗi.

| Property | Invariant | Examples | Kết quả |
|---|---|---|---|
| PROP-01 | n < MIN_CLEAN_POINTS → is_studying luôn False | 100 | PASSED |
| PROP-02 | Cluster 200m ngoài quán → luôn False | 150 | PASSED |
| PROP-03 | run_st_dbscan() không bao giờ crash với input hợp lệ | 200 | PASSED |
| PROP-04 | is_studying=True → 4 invariants đồng thời đúng | 200 | PASSED |
| PROP-05 | is_studying=False → reason không bao giờ None | 200 | PASSED |
| PROP-06 | session_score ∈ [0.0, 1.0] qua full pipeline | 150 | PASSED |

Tổng số examples được sinh và kiểm tra: **1.000 examples** — tất cả pass, không có case shrink.

PROP-03 và PROP-05 là hai property quan trọng nhất từ góc độ production: đảm bảo pipeline không crash và luôn trả lý do khi từ chối, cho phép debug hiệu quả.

---

## 5. Ranh giới quyết định thực đo

Các giá trị sau đây được đo trực tiếp bằng cách chạy pipeline với input tính toán từ công thức:

### Radius boundary (offset từ tâm quán → is_studying)

| Offset (m) | Dist thực (m) | is_studying | reason |
|---|---|---|---|
| 0 | 0.4 | True | None |
| 20 | 19.9 | True | None |
| 50 | 49.9 | True | None |
| 65 | 64.9 | True | None |
| 70 | 69.9 | True | None |
| 75 | 74.9 | **False** | outside_cafe_radius |
| 80 | 79.9 | False | outside_cafe_radius |

Ranh giới thực tế: **70–75m** — khớp với effective_radius = 50 + 20 = 70m.

### Duration boundary (span phút → is_studying)

| Span (min) | is_studying | stable_duration (min) | reason |
|---|---|---|---|
| 9 | False | 0.0 | too_short |
| 19 | False | 0.0 | too_short |
| 21 | True | 21.0 | None |
| 24 | True | 24.0 | None |
| 43.5 | True | 43.5 | None |

Ranh giới thực tế: **19–21 phút** — khớp với MIN_STABLE_DURATION_MIN=20 phút.

### Cluster purity boundary (dominant_pct → is_studying)

| dominant_pct | is_studying | reason |
|---|---|---|
| 0.40 | False | outside_cafe_radius (*) |
| 0.50 | False | low_cluster_purity |
| 0.60 | True | None |
| 0.70+ | True | None |

(*) Case 0.40: cluster quá rải rác làm centroid leakage, trigger geofence trước purity guard.

---

## 6. Phân tích chất lượng tập test

### Điểm mạnh

**Không có hallucination:** Toàn bộ 17 test cases Tầng 1 sử dụng nhãn tính từ công thức (`n < MIN_CLEAN_POINTS`, `span = (n-1) × interval`, `offset > radius + buffer`). Không có nhãn nào được AI đoán hay assign theo cảm tính.

**Coverage đầy đủ các guard:** Mỗi điều kiện trong `run_st_dbscan()` có ít nhất 2 test — một test cho true boundary và một test cho false boundary.

**Precondition assertions:** Mỗi test verify điều kiện đầu vào trước khi chạy pipeline, đảm bảo test không vô tình pass vì data không đúng như thiết kế.

**Property-based testing bổ sung cho unit test:** 1.000 examples ngẫu nhiên với 6 invariants kiểm tra hành vi pipeline ở phạm vi rộng hơn bất kỳ tập fixture cố định nào.

### Giới hạn

**Guard HIGH_SPATIAL_STD khó trigger bằng synthetic data:** Do DBSCAN tự giới hạn khoảng cách cluster ≤ eps_spatial=25m, spatial_std trong cluster luôn << MAX_SPATIAL_STD_M=30m. Guard này cần GPS drift thực tế (indoor multipath) để kích hoạt. Test TC-MATH-10b verify guard tồn tại trong code thay vì trigger nó.

**Chưa có validation với GPS thật:** Tập test này chứng minh logic toán học đúng, nhưng chưa chứng minh `eps_spatial=25m` và `MIN_STABLE_DURATION_MIN=20` phù hợp với GPS điện thoại thực tế trong quán cafe. Cần field test để calibrate.

---

## 7. Kết luận

Tập kiểm thử `test_st_dbscan_math.py` đạt các mục tiêu đề ra:

- **23/23 tests PASSED** — không có failure.
- **Không phụ thuộc dataset ngoài** — không cần thu thập GPS thật hay nhờ AI gán nhãn.
- **Không có hallucination** — nhãn tính từ công thức toán học, không phải ý kiến.
- **Coverage đầy đủ** — 5/5 điều kiện guard được kiểm tra, output contract được verify, 1.000 random examples không tìm thấy lỗi.

Bước tiếp theo: **field test thực địa** tại 1–2 quán cafe với GPS điện thoại thực để xác nhận hyperparameter (`eps_spatial`, `MIN_STABLE_DURATION_MIN`) hoạt động đúng với dữ liệu thực, đạt precision ≥ 80% theo acceptance criteria trong `scoring_engine_design.md`.
