# UI Flow Document
## StudyCafe Analytics System

**Phiên bản:** v1.1
**Ngày cập nhật:** 30/04/2026

---

## 1. Mục tiêu tài liệu

Tài liệu này mô tả luồng sử dụng và các màn hình chính của hệ thống StudyCafe Analytics System ở mức đủ để bắt đầu code frontend.

Mục tiêu:
- Chốt các màn hình cần có.
- Chốt user flow chính.
- Tránh làm frontend lan man vượt quá scope.
- Đảm bảo giao diện đủ đơn giản cho mobile web demo.

---

## 2. Nguyên tắc UI

- Ưu tiên **mobile-first**.
- Giao diện tối giản, dễ thao tác ngoài thực tế.
- Mỗi màn hình chỉ nên có 1 hành động chính.
- Tối ưu cho demo: ít màn hình, rõ trạng thái, ít phụ thuộc bản đồ.

---

## 3. Danh sách màn hình

| Mã màn | Tên màn hình | Loại | Mục tiêu |
|---|---|---|---|
| S1 | Home / Tracking Screen | Core | Bắt đầu và kết thúc session |
| S2 | Session Active Screen | Core | Hiển thị trạng thái tracking đang chạy |
| S3 | Result / Summary Screen | Core | Thông báo kết thúc session |
| S4 | Cafe List Screen | Core | Xem quán gần nhất và điểm đánh giá |
| S5 | Suggest Cafe Screen | Optional | Đề xuất thêm quán mới qua Google Places |

---

## 4. User flow chính

```
Mở web app
   ↓
S1. Home / Tracking Screen
   ↓
Cho phép GPS
   ↓
Bấm "Bắt đầu học"
   ↓
S2. Session Active Screen
   (GPS gửi định kỳ mỗi 60 giây)
   ↓
Bấm "Kết thúc"
   ↓
S3. Result / Summary Screen
   ↓
   ├── Về Home → S1
   └── Xem danh sách quán → S4
                              ↓
                     [Optional] Đề xuất quán → S5
                              ↓
                         Quay lại → S4
```

---

## 5. Mô tả từng màn hình

### 5.1 S1 — Home / Tracking Screen

#### Mục tiêu
Màn hình vào đầu tiên. Cho phép user hiểu app dùng để làm gì và bắt đầu session.

#### Thành phần chính
- Tên dự án + mô tả ngắn
- Trạng thái GPS: chưa cấp quyền / đã sẵn sàng
- Nút chính: **Bắt đầu học**
- Nút phụ: **Xem danh sách quán**

#### Wireframe
```
┌─────────────────────────────┐
│  StudyCafe Analytics        │
│  Đánh giá quán học qua GPS  │
│                             │
│  GPS: ● Sẵn sàng            │
│                             │
│  [ Bắt đầu học ]            │
│  [ Xem danh sách quán ]     │
└─────────────────────────────┘
```

#### Hành vi
- Nếu GPS chưa được cấp quyền → khi bấm "Bắt đầu học" hiện prompt xin quyền.
- Nếu user từ chối GPS → hiển thị thông báo lỗi + hướng dẫn bật lại.
- GPS status tự cập nhật khi quyền thay đổi.

---

### 5.2 S2 — Session Active Screen

#### Mục tiêu
Cho user biết session đang chạy và hệ thống đang tracking GPS.

#### Thành phần chính
- Trạng thái: Đang theo dõi
- Đồng hồ thời gian session (tăng real-time)
- Số điểm GPS đã ghi nhận
- Nút chính: **Kết thúc**
- Gợi ý giữ app mở

#### Wireframe
```
┌─────────────────────────────┐
│  Đang theo dõi phiên học    │
│                             │
│  ⏱  00:37:12               │
│  📍 37 điểm GPS             │
│  Status: Tracking...        │
│                             │
│  Giữ màn hình sáng để       │
│  tracking không bị ngắt     │
│                             │
│  [ Kết thúc ]               │
└─────────────────────────────┘
```

#### Hành vi
- Đồng hồ tăng theo giây.
- Frontend gửi GPS định kỳ mỗi 60 giây.
- Nếu GPS mất tạm thời → hiển thị cảnh báo nhẹ, không crash UI.
- Nếu mạng mất → retry GPS request, không dừng session.

---

### 5.3 S3 — Result / Summary Screen

#### Mục tiêu
Xác nhận session đã kết thúc và thông báo dữ liệu đã được ghi nhận.

#### Thành phần chính
- Thông báo kết thúc thành công
- Tổng thời gian session
- Số điểm GPS đã thu thập
- Nút về Home
- Nút xem danh sách quán

#### Wireframe
```
┌─────────────────────────────┐
│  Phiên học đã kết thúc ✓    │
│                             │
│  Thời gian: 92 phút         │
│  GPS logs:  92 điểm         │
│                             │
│  Dữ liệu đã được ghi nhận   │
│                             │
│  [ Về trang chủ ]           │
│  [ Xem danh sách quán ]     │
└─────────────────────────────┘
```

#### Ghi chú
- Chưa hiển thị behavior score ngay tại đây vì scoring engine
  có thể chưa chạy xong real-time.
- Chỉ cần thông báo "Dữ liệu đã được ghi nhận" là đủ.

---

### 5.4 S4 — Cafe List Screen

#### Mục tiêu
Hiển thị danh sách quán gần nhất dựa trên GPS hiện tại,
kèm điểm đánh giá hành vi và link Google Maps.

#### Thành phần chính
- Danh sách quán sort theo khoảng cách tăng dần
- Bộ lọc giới hạn khoảng cách: 5km, 10km, không giới hạn
- Mỗi item gồm:
  - Tên quán
  - Địa chỉ ngắn
  - Khoảng cách từ vị trí hiện tại
  - Điểm hành vi hoặc badge "Chưa đủ dữ liệu"
  - Nút **Mở Maps** → mở Google Maps URL
- Nút về Home
- Nút đề xuất quán mới [Optional]

#### Wireframe
```
┌─────────────────────────────┐
│  Quán gần bạn nhất          │
│  [ 5km ] [ 10km ] [ Tất cả ]│
│                             │
│  Cafe A              230m   │
│  123 Phố X                  │
│  Score: 8.3 ★               │
│  [ Mở Maps ]                │
│  ─────────────────────────  │
│  Cafe B              480m   │
│  456 Phố Y                  │
│  Chưa đủ dữ liệu            │
│  [ Mở Maps ]                │
│  ─────────────────────────  │
│  Cafe C              1.2km  │
│  789 Phố Z                  │
│  Score: 6.1 ★               │
│  [ Mở Maps ]                │
│                             │
│  [ + Đề xuất quán mới ]     │
│  [ Về trang chủ ]           │
└─────────────────────────────┘
```

#### Hành vi
- Khi vào màn này, frontend lấy GPS hiện tại và gọi
  `GET /api/cafes?lat=...&lng=...&radius=5000`
- Filter mặc định là 5km.
- Khi user chọn 10km, frontend gọi lại `GET /api/cafes?lat=...&lng=...&radius=10000`.
- Khi user chọn "Không giới hạn", frontend gọi lại `GET /api/cafes?lat=...&lng=...` và không gửi `radius`.
- Danh sách luôn hiển thị theo thứ tự gần đến xa dựa trên response backend.
- Hiển thị khoảng cách dạng "230m" nếu < 1000m, "1.2km" nếu >= 1000m.
- Nút "Mở Maps" mở Google Maps URL trong tab mới.
- Nếu GPS không sẵn sàng → fallback về list tĩnh `GET /api/cafes`
  và không hiển thị khoảng cách hoặc bộ lọc khoảng cách.

---

### 5.5 S5 — Suggest Cafe Screen [Optional]

#### Mục tiêu
Cho phép user tìm và đề xuất quán chưa có trong hệ thống
thông qua Google Places Autocomplete.

#### Phụ thuộc
- Google Places API Key
- Google Maps JS SDK với Places library
- Chỉ load SDK khi user mở màn này để tránh nặng trang

#### Thành phần chính
- Ô tìm kiếm tên quán (gọi Google Places Autocomplete)
- Danh sách gợi ý từ Google
- Preview thông tin quán đã chọn (tên, địa chỉ)
- Nút xác nhận submit
- Thông báo "Đã ghi nhận, chờ duyệt"

#### Wireframe
```
┌─────────────────────────────┐
│  Đề xuất quán mới           │
│                             │
│  [ Tìm tên quán...       ]  │
│                             │
│  > Cafe XYZ - 789 Phố Z     │
│  > Cafe ABC - 101 Phố W     │
│                             │
│  ─────────────────────────  │
│  Đã chọn: Cafe XYZ          │
│  Địa chỉ: 789 Phố Z         │
│                             │
│  [ Gửi đề xuất ]            │
│  [ Huỷ ]                    │
└─────────────────────────────┘
```

#### Hành vi
- Ô tìm kiếm trigger Google Places Autocomplete sau khi user gõ >= 3 ký tự.
- Khi user chọn một gợi ý, tọa độ lat/lng được tự động điền từ Places API.
- Bấm "Gửi đề xuất" → gọi `POST /api/cafes/suggest`.
- Sau khi submit thành công → hiển thị thông báo "Đã ghi nhận, chờ duyệt"
  → tự động quay về S4 sau 2 giây.

---

## 6. Navigation map

| Từ | Đến | Trigger |
|---|---|---|
| S1 | S2 | Bấm "Bắt đầu học" |
| S2 | S3 | Bấm "Kết thúc" |
| S3 | S1 | Bấm "Về trang chủ" |
| S3 | S4 | Bấm "Xem danh sách quán" |
| S1 | S4 | Bấm "Xem danh sách quán" |
| S4 | S1 | Bấm "Về trang chủ" |
| S4 | S5 | Bấm "+ Đề xuất quán mới" [Optional] |
| S5 | S4 | Submit thành công hoặc bấm "Huỷ" |

---

## 7. UI States

### 7.1 GPS State
| State | Mô tả | Hiển thị |
|---|---|---|
| `idle` | Chưa xin quyền | Badge xám "GPS chưa bật" |
| `ready` | Đã có thể lấy vị trí | Badge xanh "Sẵn sàng" |
| `tracking` | Đang gửi GPS trong session | Badge xanh nhấp nháy |
| `error` | Không lấy được GPS | Badge đỏ + message |

### 7.2 Session State
| State | Màn hình hiển thị |
|---|---|
| `not_started` | S1 |
| `active` | S2 |
| `ended` | S3 |

### 7.3 Loading State
| Tình huống | Hiển thị |
|---|---|
| Đang tạo session | Spinner trên nút "Bắt đầu học" |
| Đang kết thúc session | Spinner trên nút "Kết thúc" |
| Đang tải danh sách quán | Skeleton list |
| Đang submit đề xuất quán | Spinner trên nút "Gửi đề xuất" |

---

## 8. Error States

| Tình huống | Cách xử lý |
|---|---|
| User từ chối GPS | Thông báo ngắn + hướng dẫn bật lại quyền vị trí |
| Session start thất bại | Toast lỗi gần nút Start, cho phép thử lại |
| GPS tracking gửi lỗi tạm thời | Cảnh báo nhẹ trên S2, không dừng session |
| Không tải được danh sách quán | Thông báo lỗi + nút "Thử lại" |
| Suggest cafe thất bại | Toast lỗi + giữ nguyên form |

---

## 9. Responsive

- Thiết kế chuẩn cho màn hình điện thoại: 375px – 430px.
- Một cột duy nhất.
- Nút tối thiểu 44px chiều cao để dễ bấm.
- Text ngắn gọn, tối đa 2 dòng mỗi label.

---

## 10. Thành phần UI cần code

| Component | Dùng ở màn |
|---|---|
| Primary button | S1, S2, S3, S4, S5 |
| Secondary / Ghost button | S1, S3, S4, S5 |
| GPS status badge | S1, S2 |
| Session timer | S2 |
| Cafe card | S4 |
| Distance badge | S4 |
| Score badge | S4 |
| Error message block | S1, S2, S4, S5 |
| Skeleton loader | S4 |
| Search input + dropdown | S5 [Optional] |
| Toast notification | S3, S5 |

---

## 11. Phạm vi UI

### Trong scope
- 4 màn hình core (S1–S4)
- Giao diện đủ để demo end-to-end
- Nearby list với khoảng cách + Google Maps link
- 1 màn optional (S5) nếu còn thời gian

### Ngoài scope
- CMS / Admin dashboard
- Biểu đồ trực quan
- Bản đồ tương tác (Google Maps embed)
- Hệ thống tài khoản hoàn chỉnh
- Dark mode

---

## 12. Open items

- Có cần thêm màn debug nội bộ cho team test không?
- Có hiển thị tên quán đang ngồi ngay trên S2 không
  (cần backend resolve cafe_id trước khi hiển thị)?
- Có cần badge "Mock Data Mode" khi chạy demo không?

---

## 13. Ghi chú phiên bản

### v0.2
- Thêm tính năng nearby cafes cho S4
- Thêm màn S5 Suggest Cafe [Optional] với Google Places Autocomplete
- Thêm bảng navigation map, UI states, error states đầy đủ hơn
- Cập nhật danh sách thành phần UI

### v0.1
- Khởi tạo tài liệu với 4 màn hình cơ bản

### v1.0
- Phát hành phiên bản chính thức 1.0

### v1.1
- Bổ sung filter khoảng cách cho S4: 5km, 10km, không giới hạn.
- Chốt S4 dùng `/api/cafes` với query GPS để nhận `distance_meters` và danh sách sort gần đến xa.
