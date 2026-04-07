# API Design Document
## StudyCafe Analytics System

**Phiên bản:** v0.1  
**Ngày tạo:** 07/04/2026

---

## 1. Mục tiêu tài liệu

Tài liệu này mô tả thiết kế API và contract giao tiếp giữa frontend, backend, database và scoring engine trong hệ thống StudyCafe Analytics System.

Mục tiêu của tài liệu:
- Chốt endpoint để code backend/frontend không lệch nhau.
- Chốt request/response schema.
- Chốt error handling cơ bản.
- Chốt contract dữ liệu mà backend sẽ cung cấp cho scoring engine và nhận lại kết quả.

---

## 2. Nguyên tắc thiết kế API

- Ưu tiên đơn giản, dễ demo, dễ tích hợp.
- Prefix thống nhất: `/api/`
- Dữ liệu trao đổi ở định dạng JSON, trừ API export file Excel.
- Chưa triển khai auth phức tạp; dùng `device_id` cho mục đích demo.
- Mọi timestamp dùng ISO 8601.

---

## 3. Thực thể chính

- **Cafe**: quán cafe mẫu để hệ thống đánh giá.
- **Session**: một phiên học tập của người dùng.
- **GPS Log**: điểm dữ liệu vị trí trong session.
- **Cafe Score**: kết quả đánh giá hành vi theo quán.

---

## 4. Danh sách endpoint

| Method | Endpoint | Mục đích |
|---|---|---|
| POST | `/api/session/start` | Bắt đầu session |
| POST | `/api/tracking` | Gửi GPS log |
| POST | `/api/session/end` | Kết thúc session |
| GET | `/api/cafes` | Lấy danh sách quán |
| GET | `/api/session/{session_id}` | Xem thông tin session |
| GET | `/api/report/export` | Xuất báo cáo Excel |
| POST | `/api/mock-data/import` | Nạp mock data để test |
| GET | `/api/cafes/nearby` | Lấy quán gần nhất theo GPS [Optional] |
| POST | `/api/cafes/suggest`               | Đề xuất thêm quán mới [Optional]     |
| POST | `/api/admin/cafes/{cafe_id}/approve`| Admin duyệt quán pending [Optional]  |

---

## 5. API chi tiết

### 5.1 POST `/api/session/start`

#### Mục đích
Tạo một session mới khi người dùng bắt đầu học.

#### Request Body
```json
{
  "device_id": "string",
  "cafe_id": 1
}
```

#### Ghi chú
- `device_id` là bắt buộc.
- `cafe_id` có thể null hoặc không gửi.
- Nếu `cafe_id` chưa có, backend sẽ resolve sau dựa trên GPS đầu tiên hợp lệ.

#### Response 200
```json
{
  "status": "ok",
  "session_id": "uuid-string",
  "started_at": "2026-04-07T09:00:00Z"
}
```

#### Response 400
```json
{
  "status": "error",
  "message": "device_id is required"
}
```

---

### 5.2 POST `/api/tracking`

#### Mục đích
Nhận một điểm GPS từ frontend trong lúc session đang diễn ra.

#### Request Body
```json
{
  "device_id": "string",
  "session_id": "uuid-string",
  "lat": 21.0285,
  "lng": 105.8542,
  "accuracy": 12.5,
  "timestamp": "2026-04-07T09:01:00Z"
}
```

#### Rule
- Backend cần kiểm tra `session_id` tồn tại.
- Backend cần chống duplicate cơ bản theo `(session_id, timestamp)`.
- Nếu đây là GPS đầu tiên và session chưa có `cafe_id`, backend có thể resolve quán gần nhất.

#### Response 200
```json
{
  "status": "ok",
  "log_id": 123
}
```

#### Response 404
```json
{
  "status": "error",
  "message": "session not found"
}
```

#### Response 422
```json
{
  "status": "error",
  "message": "invalid coordinates"
}
```

---

### 5.3 POST `/api/session/end`

#### Mục đích
Kết thúc session và trigger pipeline scoring nếu cần.

#### Request Body
```json
{
  "session_id": "uuid-string"
}
```

#### Response 200
```json
{
  "status": "ok",
  "session_id": "uuid-string",
  "ended_at": "2026-04-07T11:00:00Z",
  "duration_min": 120
}
```

#### Ghi chú
- Sau khi kết thúc session, backend có thể:
  - gọi scoring engine ngay,
  - hoặc đánh dấu session chờ xử lý batch.
- Quyết định cuối cùng phụ thuộc vào tài liệu `scoring_engine_design.md`.

---

### 5.4 GET `/api/cafes`

#### Mục đích
Lấy danh sách quán cafe và điểm đánh giá hiện tại.

#### Response 200
```json
[
  {
    "cafe_id": 1,
    "name": "Cafe A",
    "address": "123 Pho X",
    "center_lat": 21.0285,
    "center_lng": 105.8542,
    "radius_meters": 50,
    "behavior_score": 8.3,
    "has_enough_data": true
  }
]
```

---

### 5.5 GET `/api/session/{session_id}`

#### Mục đích
Lấy chi tiết session để debug hoặc kiểm tra.

#### Response 200
```json
{
  "session_id": "uuid-string",
  "device_id": "device-001",
  "cafe_id": 1,
  "start_time": "2026-04-07T09:00:00Z",
  "end_time": "2026-04-07T11:00:00Z",
  "duration_min": 120,
  "gps_log_count": 120,
  "status": "completed"
}
```

---

### 5.6 GET `/api/report/export`

#### Mục đích
Xuất báo cáo tổng hợp dưới dạng file Excel.

#### Response 200
- File download `.xlsx`
- Header gợi ý:

```http
Content-Disposition: attachment; filename="studycafe_report.xlsx"
```

---

### 5.7 POST `/api/mock-data/import`

#### Mục đích
Nạp mock data để test pipeline mà không cần đi thực tế.

#### Request Body
```json
{
  "source": "mock_dataset_v1"
}
```

#### Response 200
```json
{
  "status": "ok",
  "imported_sessions": 30,
  "imported_logs": 1800
}
```

### 5.8 GET `/api/cafes/nearby` [Optional]

#### Mục đích
Trả về danh sách quán gần nhất dựa trên tọa độ hiện tại của user,
kèm đánh giá của hệ thống và link Google Maps.

#### Query Parameters
- `lat` (double): Vĩ độ hiện tại.
- `lng` (double): Kinh độ hiện tại.
- `radius` (integer, optional): Bán kính tìm kiếm (mét), mặc định 500.
- `limit` (integer, optional): Số quán trả về, mặc định 5, tối đa 10

#### Logic xử lý
1. Nhận lat/lng từ query param
2. Tính khoảng cách Haversine từ user đến từng quán trong bảng `cafes`
3. Sort theo khoảng cách tăng dần
4. Trả về top N

#### Google Maps URL
Không cần API Key. Ghép từ tọa độ quán:
```python
# Mở pin tọa độ quán
f"https://www.google.com/maps?q={cafe.center_lat},{cafe.center_lng}"

# Hoặc mở chỉ đường từ user
f"https://www.google.com/maps/dir/?api=1&destination={cafe.center_lat},{cafe.center_lng}"
```

#### Response 200
```json
[
  {
    "cafe_id": 1,
    "name": "Cafe A",
    "address": "123 Phố X",
    "distance_meters": 230,
    "center_lat": 21.0285,
    "center_lng": 105.8542,
    "behavior_score": 8.3,
    "has_enough_data": true,
    "google_maps_url": "https://www.google.com/maps?q=21.0285,105.8542"
  }
]
```

#### Response 400
```json
{ "status": "error", "message": "lat and lng are required" }
```

### 5.9 POST `/api/cafes/suggest` [Optional]

#### Mục đích
Nhận thông tin quán mới do user đề xuất, tọa độ đã được resolve
từ Google Places ở phía frontend trước khi gửi lên.

#### Request Body
```json
{
  "device_id": "string",
  "name": "string",
  "address": "string",
  "center_lat": 21.0285,
  "center_lng": 105.8542,
  "google_place_id": "ChIJ..."
}
```

#### Ghi chú
- `google_place_id` lưu lại để sau này có thể dùng tạo Google Maps URL
  chính xác theo Place thay vì chỉ dùng tọa độ.
- Quán tạo ra mặc định có `status = 'pending'`.
- Không hiển thị trong `/api/cafes` hay `/api/cafes/nearby` cho đến
  khi được admin approve.

#### Response 200
```json
{
  "status": "ok",
  "cafe_id": 6,
  "pending": true,
  "message": "Quán đã được ghi nhận, chờ duyệt"
}
```

---

### 5.10 POST `/api/admin/cafes/{cafe_id}/approve` [Optional — Internal]

#### Mục đích
Admin kích hoạt một quán đang ở trạng thái pending.
Endpoint nội bộ, không expose ra ngoài.

#### Response 200
```json
{
  "status": "ok",
  "cafe_id": 6,
  "new_status": "active"
}
```

---

## 6. Internal Contract — Backend ↔ Scoring Engine

> Phần này là contract tạm thời. Sẽ chốt lại sau hoàn thiện `scoring_engine_design.md`.

### 6.1 Input backend cung cấp cho scoring engine
```python
{
  "session_id": "uuid-string",
  "device_id": "device-001",
  "cafe": {
    "cafe_id": 1,
    "center_lat": 21.0285,
    "center_lng": 105.8542,
    "radius_meters": 50
  },
  "gps_points": [
    {
      "lat": 21.0285,
      "lng": 105.8542,
      "accuracy": 12.5,
      "timestamp": "2026-04-07T09:01:00Z"
    }
  ]
}
```

### 6.2 Output backend kỳ vọng nhận lại
```python
{
  "session_id": "uuid-string",
  "is_studying": true,
  "stable_duration_min": 87,
  "behavior_features": {
    "dropoff": false,
    "movement_std": 5.2,
    "cluster_count": 1
  },
  "behavior_score": 0.83,
  "has_enough_data": true
}
```

### 6.3 Điểm cần chờ Scoring team chốt
- Module được gọi theo **real-time từng session** hay **batch**?
- Module trả kết quả bằng **function call**, **ghi DB**, hay **file output**?
- Feature set cuối cùng gồm những trường nào?

---

## 7. Error handling cơ bản

| HTTP Code | Ý nghĩa | Khi nào dùng |
|---|---|---|
| 200 | Thành công | Request hợp lệ |
| 400 | Bad Request | Thiếu trường bắt buộc |
| 404 | Not Found | Session/Cafe không tồn tại |
| 409 | Conflict | Dữ liệu trùng, duplicate |
| 422 | Unprocessable Entity | Tọa độ hoặc payload không hợp lệ |
| 500 | Internal Server Error | Lỗi server không mong muốn |

---

## 8. Database schema mức API

> Đây là mức đủ để code backend. Schema chi tiết có thể refine thêm sau.

### 8.1 `cafes`
```sql
CREATE TABLE cafes (
    cafe_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    center_lat DOUBLE PRECISION NOT NULL,
    center_lng DOUBLE PRECISION NOT NULL,
    radius_meters INTEGER DEFAULT 50,
    status           VARCHAR(16) DEFAULT 'active',
    -- 'active'   : quán mặc định / đã được duyệt
    -- 'pending'  : do user đề xuất, chờ admin duyệt
    -- 'disabled' : tắt bởi admin
    submitted_by     VARCHAR(64),        -- device_id người đề xuất, null nếu hardcode
    google_place_id  VARCHAR(255)        -- lưu Place ID từ Google Places [Optional]
);
```

### 8.2 `sessions`
```sql
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    cafe_id INTEGER REFERENCES cafes(cafe_id),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    duration_min FLOAT,
    status VARCHAR(32) DEFAULT 'active'
);
```

### 8.3 `gps_logs`
```sql
CREATE TABLE gps_logs (
    log_id BIGSERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(session_id),
    device_id VARCHAR(64),
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    accuracy_m FLOAT,
    timestamp TIMESTAMPTZ NOT NULL,
    is_noise BOOLEAN DEFAULT FALSE,
    UNIQUE (session_id, timestamp)
);

CREATE INDEX idx_gps_session_time ON gps_logs(session_id, timestamp);
CREATE INDEX idx_gps_device_time ON gps_logs(device_id, timestamp);
CREATE INDEX idx_gps_timestamp ON gps_logs(timestamp);
```

### 8.4 `cafe_scores`
```sql
CREATE TABLE cafe_scores (
    score_id SERIAL PRIMARY KEY,
    cafe_id INTEGER REFERENCES cafes(cafe_id),
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    total_visits INTEGER,
    avg_duration FLOAT,
    dropoff_rate FLOAT,
    behavior_score FLOAT,
    has_enough_data BOOLEAN DEFAULT FALSE
);
```

---

## 9. Open items

- Chờ chốt input/output cuối của scoring engine.
- Chưa chốt endpoint admin/debug riêng.
- Chưa chốt response format cho frontend dashboard nếu sau này cần màn hình admin.

---

## 10. Ghi chú phiên bản

### v0.1
- Tạo khung API để bắt đầu code backend/frontend.
- Chưa finalize phần scoring engine contract.
