# Requirement Analysis Document
**Dự án:** StudyCafe Analytic System 
**Phụ đề:** Hệ thống đánh giá địa điểm học tập qua hành vi GPS
**Thời gian triển khai:** 1 tháng (4 tuần)  
**Phiên bản tài liệu:** 0.1

**Lần cuối chỉnh sửa:** 05/04/2026  

---

## 1. MỤC TIÊU DỰ ÁN (Project Goals)

Xây dựng một hệ thống đánh giá **khách quan** chất lượng các địa điểm học tập (Quán Cafe, Thư viện) dựa trên **hành vi thực tế** của người dùng thay vì dựa vào review chủ quan.

### Vấn đề cần giải quyết
| Vấn đề hiện tại | Giải pháp của StudyCafe Analytics |
|---|---|
| Review sao trên Google Maps mang tính chủ quan | Đánh giá dựa trên dữ liệu hành vi thực tế (GPS) |
| Không biết quán nào thực sự phù hợp để học | Tính điểm dựa trên thời gian lưu trú thực tế |
| Không có dữ liệu tổng hợp để so sánh các quán | Báo cáo Excel xuất ra từ dữ liệu thật |

### Phạm vi (Scope)
- Địa điểm: Quán Cafe (3–5 quán mẫu hardcode)
- Nền tảng: Mobile Web / PWA (không cần cài app)
- Người dùng: Demo nội bộ (3 thành viên nhóm)
- Tính năng thêm (optional): Đăng nhập/đăng ký, bình luận chủ quan, bản đồ tương tác

---

## 2. KIẾN TRÚC HỆ THỐNG (System Architecture)

```
┌─────────────────────────────────────────────────────┐
│                  CLIENT (Mobile Web)                │
│                       ReactJS                       │
│     HTML5 Geolocation API → gửi GPS mỗi 60 giây     │
└────────────────────────┬────────────────────────────┘
                         │ HTTPS POST /api/tracking
                         ▼
┌─────────────────────────────────────────────────────┐
│                BACKEND API SERVER                   │
│                 FastAPI (Python)                    │
│  ┌──────────────────┐   ┌────────────────────────┐  │
│  │   REST API Layer │   │   Scoring Engine       │  │
│  │POST /api/tracking│   │  (Python: Pandas/Numpy)│  │
│  │GET /api/report/* │   │  Noise Filter + Score  │  │
│  └──────────────────┘   └────────────────────────┘  │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│               DATABASE (PostgreSQL)                 │
│        Time-series GPS data storage                 │
│    gps_logs | cafes | sessions | score_results      │
└─────────────────────────────────────────────────────┘
                         │
                   Docker Compose
```

### Tech Stack tổng hợp
| Layer | Công nghệ | Ghi chú |
|---|---|---|
| Frontend | ReactJS | Tối ưu mobile, không cần framework nặng |
| Backend API | FastAPI (Python) | Ưu tiên — tích hợp tốt với Pandas |
| Database | PostgreSQL | Lưu time-series GPS, dễ query theo thời gian |
| Scoring Engine | Python (Pandas, Numpy) | Tích hợp thẳng vào Backend |
| Deployment | Docker Compose | |
| Export | openpyxl / xlsxwriter | Xuất file .xlsx |

---

## 3. YÊU CẦU CHỨC NĂNG (Functional Requirements)

### 3.1 Module Frontend — Thiết bị người dùng

#### FR1 — Cấp quyền GPS
- **Mô tả:** Giao diện yêu cầu người dùng cho phép truy cập vị trí qua HTML5 Geolocation API
- **Input:** Hành động người dùng (bấm "Cho phép" trên trình duyệt)
- **Output:** `navigator.geolocation` được cấp quyền, tọa độ đầu tiên được lấy
- **Điều kiện lỗi:** Người dùng từ chối → Hiển thị thông báo hướng dẫn bật lại

#### FR2 — Bắt đầu / Kết thúc Session
- **Mô tả:** Nút bấm để bắt đầu và kết thúc một phiên học tập
- **Input:** Sự kiện click của người dùng
- **Output:** Tạo `session_id` mới, ghi `start_time` / `end_time` vào DB
- **UI:** Nút "Bắt đầu học" → đổi thành "Kết thúc" (kèm đồng hồ đếm giờ hiển thị)

#### FR3 — Tracking GPS ngầm
- **Mô tả:** Khi đang trong session, trình duyệt tự động gửi tọa độ về Backend
- **Interval:** Mỗi **60 giây** / lần
- **Chống trùng khi retry:** Client gửi lại request nếu không nhận response trong 5s. Server dùng UNIQUE constraint `(session_id, device_id, timestamp)` để reject duplicate — trả về 200 OK với `log_id` của bản ghi đã tồn tại.
- **Payload gửi lên:**
```json
{
  "device_id": "uuid-xxxx",
  "session_id": "uuid-yyyy",
  "lat": 21.0285,
  "lng": 105.8542,
  "accuracy": 15.0,
  "timestamp": "2026-04-05T14:30:00Z"
}
```
- **Điều kiện dừng:** Người dùng bấm "Kết thúc" hoặc đóng tab

---

### 3.2 Module Backend — API & Database

#### FR4 — Ingest Data GPS
- **Endpoint:** `POST /api/tracking`
- **Mô tả:** Nhận luồng data GPS liên tục, ghi vào bảng `gps_logs`
- **Hiệu năng:** Chấp nhận nhiều request đồng thời (async FastAPI)
- **Response:**
```json
{ "status": "ok", "log_id": 12345 }
```

#### FR5 — Master Data Quán Cafe
- **Mô tả:** Bảng `cafes` lưu danh sách quán mẫu (hardcode 3–5 quán)
- **Cấu trúc dữ liệu:**

| Trường | Kiểu | Mô tả |
|---|---|---|
| `cafe_id` | UUID / INT | Khóa chính |
| `name` | VARCHAR | Tên quán |
| `address` | TEXT | Địa chỉ |
| `center_lat` | FLOAT | Vĩ độ trung tâm |
| `center_lng` | FLOAT | Kinh độ trung tâm |
| `radius_m` | INT | Bán kính nhận dạng (mặc định: 50m) |

---

### 3.3 Module Scoring Engine — Xử lý dữ liệu & Đánh giá

#### FR6 — Lọc nhiễu GPS (Noise Filtering)

- **Mô tả:** Loại bỏ các điểm GPS bị nhảy sai lệch bất thường (GPS jitter)
- **Tiêu chí lọc:**
  - Điểm có `accuracy > 50m` → đánh dấu nghi ngờ
  - Tốc độ di chuyển tính từ 2 điểm liên tiếp `> 5 m/s` (18 km/h) → nhiễu (người học không di chuyển nhanh)
  - Áp dụng **rolling median** trên cửa sổ 3–5 điểm để làm mượt tọa độ
- **Input:** Raw GPS log của 1 session (list các điểm lat/lng/timestamp)
- **Output:** Cleaned GPS log (đã loại điểm nhiễu)

#### FR7 — Nhận diện hành vi "Đang học"

- **Mô tả:** Xác định người dùng đang "ngồi im" trong bán kính quán cafe
- **Điều kiện nhận diện:**
  - Tọa độ nằm trong bán kính **50m** tính từ `center_lat/lng` của quán
  - Tọa độ xê dịch không quá **20m** trong ít nhất **30 phút** liên tục
- **Công thức khoảng cách:** Haversine formula
- **Output:** `is_studying: true/false` + `stable_duration_minutes` cho mỗi session
- **Tiêu chí chấp nhận đo được:**
  - Precision ≥ 85% (trong các session được đánh dấu `is_studying=true`, ≥85% thực sự đang học)
  - Recall ≥ 80% (trong tổng số session học thực tế, ≥80% được nhận diện đúng)
  - Kiểm tra bằng bộ dữ liệu test gồm 50 session có ground truth label

#### FR8 — Công thức tính điểm (Scoring Formula)

- **Mô tả:** Tính điểm tổng hợp cho từng quán cafe dựa trên hành vi người dùng
- **Công thức gợi ý (cần review & điều chỉnh):**

```
Score_raw = (W1 × AvgDuration_normalized) - (W2 × DropoffRate) + (W3 × ReturnRate)

Trong đó:
  AvgDuration_normalized = min(avg_session_minutes / 120, 1.0)  (chuẩn hóa về [0,1], cap tại 2 giờ)
  DropoffRate            = số session < 15 phút / tổng session
  ReturnRate             = số user quay lại ≥ 2 lần / tổng user unique
  W1 = 0.5, W2 = 0.3, W3 = 0.2  (trọng số — Long điều chỉnh)

Chuẩn hóa cuối (đảm bảo Score ∈ [0, 1]):
  Score = max(0, min(1, Score_raw))

Xử lý mẫu nhỏ (tránh bias khi ít dữ liệu):
  - Nếu total_sessions < 5: Score = NULL (chưa đủ dữ liệu)
  - Nếu total_unique_users < 3: ReturnRate = 0 (không tính factor này)
```

- **Thang điểm:** 0.0 – 1.0 (hoặc nhân 10 để ra 0–10)
- **NOTE** *"Xem phần FR8, nghĩ thử công thức Toán học nào hợp lý hơn không? Có thể thêm factor về độ ổn định tọa độ (standard deviation lat/lng) vào công thức không?"*

---

### 3.4 Module Báo cáo Admin

#### FR9 — Export Excel

- **Endpoint:** `GET /api/report/export`
- **Output:** File `.xlsx` tải về trực tiếp
- **Cấu trúc file Excel:**

| Tên quán | Địa chỉ | Tổng lượt đến | Thời gian TB (phút) | Tỷ lệ drop-off (%) | Điểm hành vi |
|---|---|---|---|---|---|
| Cafe A | 123 Phố X | 42 | 87 | 12% | 8.3 |
| Cafe B | 456 Phố Y | 28 | 34 | 41% | 4.1 |

- **NOTE** *"Thiết kế giúp cấu trúc các cột cho bảng `gps_logs` trong PostgreSQL để tiện query và xử lý Pandas nhất. Đặc biệt cần nghĩ về index theo `session_id` và `timestamp` để query time-series nhanh."*

---

## 4. YÊU CẦU PHI CHỨC NĂNG (Non-Functional Requirements)

| # | Yêu cầu | Mô tả chi tiết |
|---|---|---|
| NFR1 | **Khả dụng (Accessibility)** | Chạy trên Safari/Chrome mobile, không cần cài app |
| NFR2 | **Bảo mật (Security)** | Dùng `device_id` (random UUID) thay JWT để tiết kiệm thời gian — chấp nhận cho demo |
| NFR3 | **Hiệu năng (Performance)** | API `/tracking` response < 500ms dưới tải 10 concurrent requests/giây; tracking interval 60s không làm hao pin |
| NFR4 | **Độ tin cậy GPS** | Chấp nhận sai số GPS thực tế của điện thoại (~5–20m) |
| NFR5 | **Khả năng triển khai** | Docker Compose 1 lệnh `docker-compose up` là chạy được toàn bộ |

---

## 5. CẤU TRÚC DATABASE (Database Schema)

### Bảng `cafes` 
```sql
CREATE TABLE cafes (
    cafe_id     SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    address     TEXT,
    center_lat  DOUBLE PRECISION NOT NULL,
    center_lng  DOUBLE PRECISION NOT NULL,
    radius_m    INTEGER DEFAULT 50
);
```

### Bảng `sessions` (Quản lý phiên học)
```sql
CREATE TABLE sessions (
    session_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id   VARCHAR(64) NOT NULL,
    cafe_id     INTEGER REFERENCES cafes(cafe_id),
    start_time  TIMESTAMPTZ NOT NULL,
    end_time    TIMESTAMPTZ,
    duration_min FLOAT  -- Tính khi kết thúc session
);
```

### Bảng `gps_logs` (Time-series GPS)
```sql
CREATE TABLE gps_logs (
    log_id      BIGSERIAL PRIMARY KEY,
    session_id  UUID REFERENCES sessions(session_id),
    device_id   VARCHAR(64),
    lat         DOUBLE PRECISION NOT NULL,
    lng         DOUBLE PRECISION NOT NULL,
    accuracy_m  FLOAT,
    timestamp   TIMESTAMPTZ NOT NULL,
    is_noise    BOOLEAN DEFAULT FALSE,  -- đánh dấu sau khi filter

    -- Idempotency: chống trùng khi client retry
    UNIQUE (session_id, device_id, timestamp)
);
-- Index gợi ý:
CREATE INDEX idx_gps_session ON gps_logs(session_id, timestamp);
CREATE INDEX idx_gps_device_time ON gps_logs(device_id, timestamp);
CREATE INDEX idx_gps_timestamp ON gps_logs(timestamp);
```

### Bảng `cafe_scores`
```sql
CREATE TABLE cafe_scores (
    score_id        SERIAL PRIMARY KEY,
    cafe_id         INTEGER REFERENCES cafes(cafe_id),
    computed_at     TIMESTAMPTZ DEFAULT NOW(),
    total_visits    INTEGER,
    avg_duration    FLOAT,
    dropoff_rate    FLOAT,
    behavior_score  FLOAT  -- Output của FR8
);
```

---

## 6. PHÂN CHIA NHIỆM VỤ (Task Delegation)

> ⚠️ **TODO:** Cần điền chi tiết task cho từng thành viên theo tuần trước khi bắt đầu sprint.

### Võ Viết Đức — Tech Lead & Fullstack / DevOps

| Task | Module | Tuần |
|---|---|---|
|  |  |  |


### 👤 Hà Hoàng Long — Thuật toán & Logic (OOP)

| Task | Module | Tuần |
|---|---|---|
|  |  |  |


### 👤 Nguyễn Anh Tú — Data Processing & Reporting

| Task | Module | Tuần |
|---|---|---|
|  |  |  |

---

## 7. API CONTRACT 

### `POST /api/tracking` — Nhận GPS
```
Request Body (JSON):
{
  "device_id":  string (UUID),
  "session_id": string (UUID),
  "lat":        float,
  "lng":        float,
  "accuracy":   float (meters),
  "timestamp":  string (ISO 8601)
}

Response 200:
{ "status": "ok", "log_id": int }

Response 422:
{ "error": "Invalid coordinates" }
```

### `POST /api/session/start` — Bắt đầu session
```
Request Body: { "device_id": string, "cafe_id": int (optional) }
Response 200: { "session_id": "uuid-xxxx", "started_at": "ISO timestamp" }

Fallback khi cafe_id null:
  - Backend sẽ dùng tọa độ GPS đầu tiên nhận được trong session
  - Tính khoảng cách tới tất cả các quán trong bảng cafes
  - Nếu nằm trong radius_m của quán nào → gán cafe_id = quán đó
  - Nếu không nằm trong quán nào → cafe_id = NULL (session không tính điểm cho quán)
```

### `POST /api/session/end` — Kết thúc session
```
Request Body: { "session_id": string }
Response 200: { "duration_min": float, "behavior_detected": bool }
```

### `GET /api/cafes` — Danh sách quán
```
Response 200: [ { "cafe_id", "name", "address", "center_lat", "center_lng", "score" } ]
```

### `GET /api/report/export` — Export Excel
```
Response 200: File download (.xlsx)
Content-Disposition: attachment; filename="geostudy_report.xlsx"
```

---

## 8. LỘ TRÌNH TRIỂN KHAI (Milestones)

> ⚠️ **TODO:** Cần bổ sung deliverables cụ thể cho từng tuần và assign owner.

```
TUẦN 1: NỀN TẢNG
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Đức:  
 Long: 
 Tú:   

TUẦN 2: 
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TUẦN 3:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 
TUẦN 4:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```

---

## 9. RỦI RO & PHƯƠNG ÁN DỰ PHÒNG (Risk Management)

| Rủi ro | Khả năng | Phương án xử lý |
|---|---|---|
| GPS điện thoại không chính xác trong nhà | Cao | Mở rộng bán kính lên 100m; ghi nhận `accuracy` để filter |
| Trình duyệt mobile dừng tracking khi tắt màn hình | Cao | Dùng Wake Lock API; hướng dẫn user giữ màn hình sáng |
| Công thức tính điểm cho kết quả không hợp lý | Trung bình | Chuẩn hóa dữ liệu test tuần 1; Long review công thức trước tuần 2 |
| Không đủ data thực tế để validate | Trung bình | Script sinh data GPS giả (Tú viết tuần 1) |
| Deploy VPS gặp sự cố | Thấp | Docker Compose → demo local vẫn được |

---

## 10. ĐỊNH NGHĨA HOÀN THÀNH (Definition of Done)

Dự án coi là **hoàn thành** khi đáp ứng đủ các tiêu chí sau:
(Có thể thay đổi sau khi hỏi mentor hoặc trong quá trình phát triển)

- [ ] Người dùng mở Chrome/Safari mobile, bấm nút → tọa độ GPS được gửi về server
- [ ] Hệ thống nhận dạng được session "đang học" và phân biệt với "chỉ đi qua"
- [ ] Điểm đánh giá hành vi của ít nhất 3 quán cafe được tính và hiển thị
- [ ] Export được file Excel chứa báo cáo tổng hợp
- [ ] Toàn bộ hệ thống chạy được bằng `docker-compose up`
- [ ] Demo live được trước Mentor trong 5–10 phút

---
*Mọi thay đổi requirement sau Tuần 1 cần được cả nhóm đồng thuận trước khi cập nhật.*
