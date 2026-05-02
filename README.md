# StudyCafe Analytics System

## 1. Giới thiệu (Project Overview)
- Tóm tắt dự án: Chấm điểm không gian học tập (quán cafe) dựa trên hành vi GPS thực tế của người dùng thay vì dựa vào review cảm tính.
- Giải quyết bài toán: Loại bỏ review ảo, định lượng hoá chính xác mức độ tập trung thông qua phân tích không gian - thời gian (ST-DBSCAN) và hệ thống chấm điểm Bayesian Average.

## 2. Tính năng cốt lõi (Core Features)
- Thu thập và lọc nhiễu GPS: Xử lý GPS drift, tín hiệu ảo trong nhà bằng bộ lọc đa lớp sử dụng ngưỡng độ chính xác, giới hạn tốc độ và Hampel Identifier.
- Phát hiện hành vi học tập: Loại bỏ các hành vi đi lại liên tục, nhận diện chính xác các điểm dừng đủ thời gian và sự ổn định.
- Hệ thống chấm điểm khách quan: Đánh giá hành vi đám đông và xuất ra điểm quán (Behavior Score).
- Giao diện tối giản: Ứng dụng theo dõi trên nền web thiết kế cho di động, giảm thiểu rào cản thao tác.

## 3. Tech Stack (Công nghệ)
- Frontend: React (Vite), Tailwind CSS.
- Backend: FastAPI, SQLAlchemy (Async), PostgreSQL.
- Scoring Engine (AI/Data): numpy, scikit-learn, pandas, scipy.

## 4. Cấu trúc thư mục (Project Structure)
```text
studycafe-analytics/
├── backend/
│   ├── app/                 # FastAPI backend: API routes, Models, Services
│   ├── scoring_engine/      # Chứa thuật toán phân nhóm và đánh giá AI
│   └── tests/               # Unit/Integration tests cho backend
├── frontend/
│   ├── src/                 # Giao diện React Frontend
│   └── public/              # Static assets
├── docs/                    # Tài liệu nghiệp vụ, API và System Design
├── docker-compose.yml       # Tệp lệnh khởi động toàn bộ môi trường
└── requirements.txt         # Danh sách thư viện Python
```
## 5. Hướng dẫn cài đặt (Getting Started)

Hệ thống được đóng gói hoàn chỉnh bằng Docker Compose để chạy môi trường local nhanh chóng và đồng bộ.

Yêu cầu hệ thống:
- Đã cài đặt Docker và Docker Compose.

Thiết lập biến môi trường:
- Copy file `.env.example` thành `.env` tại thư mục gốc.
- Các biến môi trường trong `.env` sẽ được Docker Compose tự động nạp lên một cách bảo mật.
- Hệ thống đã đính kèm các giá trị dự phòng mặc định (fallback default) trong file Compose, nên nếu bạn không chỉnh sửa biến thì thao tác init ban đầu vẫn thành công. Tuy nhiên trong môi trường production thực tế, hãy đổi mật khẩu `POSTGRES_PASSWORD` và cài đặt `GOOGLE_PLACES_API_KEY`.

Khởi động hệ thống:
- Mở terminal tại thư mục gốc của dự án và chạy lệnh:
  `docker compose up -d --build`
- Sau khi backend sẵn sàng, service `mock-data` sẽ tự nạp mock data vào database qua endpoint `/api/mock-data/import`.

Sau khi build xong, truy cập vào ứng dụng tại:
- Frontend (Giao diện người dùng): http://localhost:5173
- Backend API (Swagger UI): http://localhost:8088/docs

Khi chạy frontend local không qua Docker và không cấu hình `.env`, frontend
mặc định gọi backend tại `http://localhost:8000`. Với Docker Compose,
`VITE_API_BASE_URL` được set sẵn thành `http://localhost:8088` để khớp port
public của backend container.

Tắt hệ thống:
- Khi muốn dừng toàn bộ các tiến trình:
  `docker compose down`

## 6. Tài liệu tham khảo (Documentation)
Mọi quyết định luồng ứng dụng và thuật toán phân tích đều được ghi chép rõ ràng trong thư mục docs/:
- docs/RequirementAnalysis.md: Yêu cầu chức năng tổng quan.
- docs/scoring_engine_design.md: Chi tiết công thức tính toán và AI pipeline.
- docs/api_design.md: Cấu trúc database và thiết kế API RESTful.
- docs/ui_flow.md: Sơ đồ tương tác luồng màn hình UI.
