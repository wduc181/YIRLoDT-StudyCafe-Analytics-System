# Requirement Analysis Document
## StudyCafe Analytics System
**Phiên bản:** v1.0
**Ngày cập nhật:** 18/04/2026  

---

# 1. Tổng quan dự án

## 1.1 Tên dự án
**StudyCafe Analytics System** — Hệ thống đánh giá địa điểm học tập qua hành vi GPS.

## 1.2 Bối cảnh
Người dùng hiện thường chọn quán cafe hoặc địa điểm học tập dựa trên review chủ quan. Tuy nhiên, các review này có thể mang tính cảm tính, không phản ánh đúng việc địa điểm đó có thực sự phù hợp để học tập hay không.

## 1.3 Mục tiêu dự án
Xây dựng một hệ thống có khả năng đánh giá mức độ phù hợp của địa điểm học tập dựa trên **hành vi thực tế của người dùng**, chủ yếu thông qua dữ liệu GPS và thời gian lưu trú, thay vì phụ thuộc hoàn toàn vào review thủ công.

## 1.4 Mục tiêu demo
Trong phạm vi đồ án, hệ thống cần:
- Cho phép người dùng mở web trên điện thoại và bắt đầu một phiên học tập.
- Thu thập dữ liệu GPS định kỳ trong suốt phiên.
- Xử lý dữ liệu để suy ra hành vi học tập.
- Tính điểm hành vi cho từng quán cafe mẫu.
- Xuất báo cáo tổng hợp ra file Excel.

---

# 2. Phạm vi dự án

## 2.1 Trong phạm vi
- Xây dựng hệ thống dạng **Mobile Web/PWA**.
- Thu thập GPS từ trình duyệt điện thoại.
- Lưu dữ liệu GPS theo session.
- Quản lý danh sách quán cafe mẫu.
- Xử lý dữ liệu GPS để phục vụ đánh giá hành vi.
- Tính điểm đánh giá quán dựa trên hành vi.
- Xuất báo cáo dạng `.xlsx`.
- Hỗ trợ **mock data** để demo và kiểm thử.

## 2.2 Ngoài phạm vi
- Đăng nhập/đăng ký người dùng hoàn chỉnh.
- Tích hợp thanh toán, loyalty, notification.
- Review chủ quan dạng sao/bình luận là chức năng bắt buộc.
- Bản đồ tương tác phức tạp.
- Phát hành ứng dụng native trên App Store / Google Play.
- Bảo mật production-level như JWT, OAuth, RBAC đầy đủ.

---

# 3. Các bên liên quan

| Vai trò | Người phụ trách | Trách nhiệm chính |
|---|---|---|
| Backend / Frontend | Võ Viết Đức | Xây API, giao diện web, database, deploy, tích hợp |
| Scoring / Logic | Hà Hoàng Long | Thiết kế logic nhận diện hành vi và tính điểm |
| Data Processing / Export  / Scoring| Nguyễn Anh Tú | Xử lí cách tính điểm, lọc nhiễu dữ liệu GPS, xử lý dữ liệu, export Excel |

---

# 4. Giả định và ràng buộc

## 4.1 Giả định
- GPS trên điện thoại **không có độ chính xác cao tuyệt đối**.
- Mock data được chấp nhận trong quá trình demo và test.
- Nhóm được tự đề xuất công thức hoặc mô hình đánh giá hành vi.
- Dự án được ưu tiên tính khả thi và khả năng demo trong 1 tháng.

## 4.2 Ràng buộc
- Nhóm chỉ có 3 người.
- Thời gian triển khai ngắn.
- Ưu tiên công nghệ đơn giản, dễ tích hợp.
- Hệ thống cần đủ rõ ràng để các module có thể làm song song.
- [OPTIONAL] Google Places API Key cần được cấp phát trước khi triển khai
  tính năng FR-B8 và FR-A7.
- [OPTIONAL]Free tier của Google Places đủ dùng cho mục đích demo.

---

# 5. Phân rã hệ thống theo module

Hệ thống được chia thành 4 module chính để dễ phân công và phát triển song song.

## 5.1 Module A — Frontend Tracking

### Mục tiêu
Cung cấp giao diện mobile web đơn giản để người dùng:
- cấp quyền GPS,
- bắt đầu/kết thúc phiên học tập,
- gửi dữ liệu vị trí định kỳ lên backend.

### Đầu vào
- Tương tác người dùng.
- Dữ liệu GPS từ trình duyệt.

### Đầu ra
- Session được tạo/kết thúc.
- Tọa độ GPS được gửi định kỳ về server.

---

## 5.2 Module B — Backend API & Data Storage

### Mục tiêu
Xây dựng backend tiếp nhận dữ liệu GPS, quản lý session, lưu database và cung cấp dữ liệu cho các module xử lý.

### Đầu vào
- GPS logs từ frontend.
- Yêu cầu export báo cáo.
- Yêu cầu truy xuất danh sách quán.

### Đầu ra
- Dữ liệu GPS lưu trong DB.
- Dữ liệu session có thể truy vấn lại.
- Dữ liệu sạch để chuyển cho Scoring Engine.
- File Excel báo cáo (thông qua module báo cáo).

---

## 5.3 Module C — Scoring Engine

### Mục tiêu
Phân tích dữ liệu GPS theo session để:
- lọc nhiễu,
- phát hiện hành vi có khả năng là “đang học”,
- tính toán điểm hành vi cho từng địa điểm.

### Ghi chú
Module này **không mô tả chi tiết thuật toán trong file này**.  
Chi tiết thiết kế model, pipeline, cách train, input/output sẽ được mô tả trong tài liệu riêng:
- `scoring_engine_design.md`

### Đầu vào ở mức hệ thống
- Danh sách GPS logs theo session.
- Thông tin quán cafe mẫu.
- Metadata của session.

### Đầu ra ở mức hệ thống
- Kết quả đánh dấu session có/không mang tính học tập.
- Các chỉ số tổng hợp của session.
- Điểm hành vi theo quán.

---

## 5.4 Module D — Reporting / Export

### Mục tiêu
Tổng hợp dữ liệu đã xử lý và xuất báo cáo dạng Excel để phục vụ demo và đối chiếu kết quả.

### Đầu vào
- Kết quả scoring theo quán.
- Dữ liệu tổng hợp về số lượt đến, thời gian trung bình, tỷ lệ rời sớm.

### Đầu ra
- File `.xlsx` chứa báo cáo tổng hợp.

---

# 6. Yêu cầu chức năng theo module

## 6.1 Module A — Frontend Tracking

### FR-A1 — Cấp quyền GPS
Hệ thống phải yêu cầu người dùng cấp quyền truy cập vị trí khi bắt đầu sử dụng.

### FR-A2 — Bắt đầu session
Hệ thống phải cho phép người dùng bắt đầu một phiên học tập bằng nút bấm.

### FR-A3 — Kết thúc session
Hệ thống phải cho phép người dùng kết thúc phiên học tập bằng nút bấm.

### FR-A4 — Gửi GPS định kỳ
Trong khi session đang hoạt động, hệ thống phải gửi dữ liệu GPS định kỳ về backend.

### FR-A5 — Hiển thị trạng thái session
Frontend phải hiển thị rõ trạng thái hiện tại: chưa bắt đầu, đang tracking, đã kết thúc.

### FR-A6 — Hiển thị quán gần nhất [Optional]
Khi user vào màn danh sách quán, hệ thống lấy GPS hiện tại và hiển thị
các quán gần nhất theo khoảng cách thực tế, bên cạnh đó là rating và link dẫn ra google map của quán.

### FR-A7 — Giao diện đề xuất quán mới [Optional]
Frontend cung cấp ô tìm kiếm tên quán tích hợp Google Places
Autocomplete. Khi user chọn một địa điểm từ gợi ý, hệ thống tự
điền tọa độ và gửi lên backend để tạo quán ở trạng thái pending.

---

## 6.2 Module B — Backend API & Data Storage

### FR-B1 — Nhận GPS logs
Backend phải có API nhận dữ liệu GPS từ frontend theo thời gian thực hoặc gần thời gian thực.

### FR-B2 — Quản lý session
Backend phải tạo và kết thúc session tương ứng với thao tác của người dùng.

### FR-B3 — Lưu trữ GPS logs
Backend phải lưu dữ liệu GPS theo session để phục vụ xử lý sau.

### FR-B4 — Quản lý danh sách quán cafe
Backend phải lưu được danh sách quán cafe mẫu với thông tin vị trí trung tâm và bán kính nhận diện.

### FR-B5 — Cung cấp dữ liệu cho scoring engine
Backend phải có cơ chế truy xuất dữ liệu GPS/session để đưa sang module Scoring Engine.

### FR-B6 — Hỗ trợ mock data
Backend phải cho phép nạp dữ liệu GPS giả lập để kiểm thử và demo.

### FR-B7 — API tìm quán gần nhất [Optional]
Backend cung cấp endpoint nhận tọa độ GPS của user và trả về danh sách
quán được sắp xếp theo khoảng cách tăng dần, kèm điểm đánh giá của hệ thống và
Google Maps URL.

### FR-B8 — Cho phép user đề xuất thêm quán mới [Optional]
User có thể submit một quán chưa có trong hệ thống thông qua Google
Places Autocomplete. Hệ thống lấy tọa độ chính xác từ Google, quán
mới sẽ ở trạng thái `pending` cho đến khi admin kích hoạt.

Phụ thuộc: Google Places API Key.
---

## 6.3 Module C — Scoring Engine

### FR-C1 — Lọc nhiễu dữ liệu GPS
Hệ thống phải có cơ chế xác định và loại bỏ hoặc đánh dấu các điểm GPS bất thường.

### FR-C2 — Phát hiện hành vi “đang học”
Hệ thống phải xác định được một session có đủ dấu hiệu để xem là hành vi học tập hay không.

### FR-C3 — Tính đặc trưng hành vi
Hệ thống phải trích xuất được các đặc trưng cần thiết từ GPS/session để phục vụ đánh giá.

### FR-C4 — Tính điểm quán
Hệ thống phải tính được điểm hành vi cho từng quán cafe dựa trên dữ liệu các session.

### FR-C5 — Trả kết quả cho backend
Scoring Engine phải trả kết quả ở dạng có thể tích hợp lại vào backend và reporting.

---

## 6.4 Module D — Reporting / Export

### FR-D1 — Tổng hợp số liệu theo quán
Hệ thống phải tính được các chỉ số tổng hợp theo từng quán.

### FR-D2 — Xuất Excel
Hệ thống phải xuất được báo cáo dưới dạng file Excel.

### FR-D3 — Hiển thị trạng thái thiếu dữ liệu
Nếu dữ liệu chưa đủ để đánh giá, hệ thống phải thể hiện rõ trạng thái “chưa đủ dữ liệu” thay vì đưa ra điểm sai lệch.

---

# 7. Yêu cầu phi chức năng

## 7.1 Tính khả dụng
- Hệ thống chạy được trên trình duyệt điện thoại phổ biến như Chrome và Safari.
- Người dùng không cần cài app native.

## 7.2 Hiệu năng
- API nhận GPS phải phản hồi đủ nhanh để phục vụ demo nhóm nhỏ.
- Hệ thống phải hoạt động ổn định với quy mô demo 3 người dùng đồng thời.

## 7.3 Khả năng bảo trì
- Hệ thống phải được chia module rõ ràng để từng thành viên có thể làm việc độc lập.
- Contract giữa backend và scoring engine cần được định nghĩa tách biệt.

## 7.4 Độ tin cậy dữ liệu
- Hệ thống phải chấp nhận GPS có sai số nhất định.
- Cần có cơ chế làm việc với mock data và dữ liệu thực song song.

## 7.5 Tính triển khai
- Hệ thống nên đóng gói được bằng Docker Compose để chạy nhanh trên máy local hoặc server demo.

---

# 8. Dữ liệu nghiệp vụ chính

## 8.1 Thực thể chính
- **Cafe**: thông tin quán cafe mẫu
- **Session**: một phiên học tập của người dùng
- **GPS Log**: một điểm dữ liệu vị trí theo thời gian
- **Cafe Score**: kết quả đánh giá hành vi của một quán

## 8.2 Quan hệ dữ liệu mức nghiệp vụ
- Một **Cafe** có thể có nhiều **Session**
- Một **Session** có nhiều **GPS Log**
- Một **Cafe** có thể có một hoặc nhiều bản ghi **Cafe Score** theo từng lần tính toán

> Chi tiết schema database sẽ được mô tả trong tài liệu thiết kế/API, không chốt hoàn toàn trong RA v0.2.

---

# 9. Phụ thuộc giữa các module

| Module | Phụ thuộc vào | Ghi chú |
|---|---|---|
| Frontend Tracking | Backend API | Gửi GPS, tạo session |
| Backend API | Database | Lưu và truy xuất dữ liệu |
| Scoring Engine | Backend + Database | Lấy dữ liệu session/GPS |
| Reporting | Backend + Scoring Engine | Dùng kết quả scoring để xuất báo cáo |

---

# 10. Milestones dự kiến

## Tuần 1 — Chốt requirement và contract
- Hoàn thiện tài liệu requirement
- Chốt cách chia module
- Chốt input/output giữa backend và scoring engine
- Dựng skeleton backend/frontend
- Chuẩn bị mock data

## Tuần 2 — Hoàn thiện pipeline cơ bản
- Frontend gửi được GPS
- Backend lưu được session và logs
- Module scoring có skeleton input/output

## Tuần 3 — Tích hợp và test
- Tích hợp scoring engine với backend
- Chạy thử bằng mock data và test thực tế
- Hoàn thiện export Excel

## Tuần 4 — Ổn định và demo
- Fix bug
- Đóng gói hệ thống
- Chuẩn bị slide và demo mentor

---

# 11. Tiêu chí hoàn thành mức requirement

Tài liệu requirement được xem là đạt mức có thể chuyển sang thiết kế/implementation khi:
- Scope đã rõ.
- Module đã tách rõ owner.
- Biết module nào cần input gì và output gì ở mức hệ thống.
- Không còn lẫn giữa requirement và implementation detail.
- Có chỗ riêng để nhóm AI/scoring tự mô tả giải pháp.

---

# 12. Các tài liệu liên quan

Sau RA v0.2, bộ tài liệu dự kiến gồm:
- `requirement_analysis.md`
- `api_design.md`
- `ui_flow.md`
- `scoring_engine_design.md`

---

# 13. Ghi chú phiên bản

## v0.2
- Viết lại theo hướng module hóa
- Tách requirement hệ thống khỏi chi tiết implementation
- Tách riêng module Scoring Engine để phục vụ tài liệu model riêng
- Phù hợp hơn với dự án nhóm 3 người, scope mock data, thời gian 1 tháng

## v0.3
- Thêm 1 số chức năng optional 

## v1.0
- Phát hành phiên bản chính thức 1.0