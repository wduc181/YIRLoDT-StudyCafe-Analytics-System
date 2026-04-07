# Scoring Engine Design Document
## StudyCafe Analytics System

**Phiên bản:** v0.1 
**Ngày tạo:** 07/04/2026

---


> File này mới chỉ là tạo khung. Nhiệm vụ là **đọc kỹ từng mục, thảo luận với nhau, rồi hoàn thiện tài liệu**.


---

## 1. Mục tiêu module

>
> Viết 3–5 câu mô tả module Scoring Engine làm gì, tại sao cần có module này, và vấn đề nó giải quyết trong hệ thống StudyCafe Analytics.


---

## 2. Phạm vi và giới hạn

>
> Liệt kê rõ:
> - Module này làm được gì?
> - Module này KHÔNG làm gì? (tránh scope creep)
> - Giả định nào module này dựa vào?

### 2.1 Trong phạm vi


### 2.2 Ngoài phạm vi


### 2.3 Giả định


---

## 3. Input Contract

> Mô tả chính xác dữ liệu module nhận từ Backend.
> Đây là **giao kèo với người làm backend** — sau khi chốt, backend sẽ code theo đúng format này.
>
> Cần trả lời:
> - Module nhận dữ liệu từ đâu? (API call, đọc DB trực tiếp, file?)
> - Format dữ liệu đầu vào là gì? (JSON, DataFrame, list?)
> - Những trường nào là bắt buộc?
> - Khi nào module được gọi? (sau mỗi session kết thúc, theo batch, theo lịch?)

### 3.1 Nguồn dữ liệu


> Gợi ý: Backend gọi module sau khi session kết thúc? Hay module tự query DB?


### 3.2 Format dữ liệu đầu vào
```python
# [ tự định nghĩa format ở đây ]
# Ví dụ gợi ý — có thể thay đổi hoàn toàn:
{
    "session_id": "...",
    "cafe_id": ...,
    "gps_points": [
        {
            "lat": ...,
            "lng": ...,
            "accuracy": ...,
            "timestamp": "..."
        }
    ]
}
```

### 3.3 Dữ liệu tham chiếu cần thêm


> Gợi ý: Ngoài GPS points, module có cần thêm gì không?
> - Thông tin quán (center_lat, center_lng, radius)?
> - Lịch sử session cũ của quán để train model?
> - Dữ liệu gì khác?


---

## 4. Pipeline tổng thể

>
> Vẽ sơ đồ luồng xử lý từ input đến output bằng ASCII hoặc mô tả từng bước.

```
[ ... ]

Gợi ý cấu trúc:
Raw GPS Input
    ↓
[ Bước 1: ? ]
    ↓
[ Bước 2: ? ]
    ↓
[ Bước n: ? ] 
    ↓
Output Score
```

---

## 5. Noise Filter

> Mô tả cách lọc nhiễu dữ liệu GPS thô.

### 5.1 Vấn đề cần giải quyết

> GPS thực tế có những loại nhiễu nào? Tại sao cần lọc? 

### 5.2 Thuật toán / Phương pháp chọn

> Dùng kỹ thuật gì? Tại sao chọn kỹ thuật đó? 
> (Gợi ý để tham khảo: rolling median, z-score, tốc độ di chuyển bất thường...)


### 5.3 Tiêu chí đánh dấu là nhiễu

> Điểm GPS nào sẽ bị loại / đánh dấu? Điều kiện cụ thể? 


### 5.4 Output của bước này
```python
# [ tự định nghĩa format output ]
```

### 5.5 Edge cases cần xử lý

---

## 6. Study Detection

> Mô tả cách phát hiện hành vi "đang học" từ dữ liệu GPS đã lọc.

### 6.1 Định nghĩa "đang học" trong hệ thống này

> thế nào là một session được coi là "đang học"?
> Mô tả bằng ngôn ngữ tự nhiên trước, rồi chuyển thành điều kiện toán học. 


### 6.2 Thuật toán / Phương pháp chọn

> Dùng thuật toán gì? Tại sao? 
> Gợi ý để tham khảo: DBSCAN, K-Means, rule-based threshold, Haversine distance...
> ```

### 6.3 Parameters và lý do chọn

>  Các tham số của thuật toán là gì? Chọn giá trị nào? Tại sao? 
> Ví dụ nếu dùng DBSCAN: eps = ? (tương đương bao nhiêu mét?), min_samples = ?


### 6.4 Output của bước này
```python

```

### 6.5 Edge cases cần xử lý

> Gợi ý: Session quá ngắn? GPS drift trong nhà? Người di chuyển liên tục?


---

## 7. Scoring Model

> Mô tả cách tính điểm hành vi cho từng quán cafe.

### 7.1 Bài toán cần giải

> Điểm hành vi của một quán thể hiện điều gì?
>  Quán nào được điểm cao? Điều kiện cụ thể là gì? 


### 7.2 Features sử dụng

> Những đặc trưng nào được đưa vào model/công thức? 
```
| Feature | Mô tả | Đơn vị | Nguồn |
|---|---|---|---|
| [ ? ] | [ ? ] | [ ? ] | [ ? ] |
```

### 7.3 Phương pháp tính điểm

> Dùng công thức trọng số? Unsupervised ML? Kết hợp?
> Mô tả rõ lý do chọn hướng tiếp cận. 

### 7.4 Công thức / Mô tả model

> Nếu dùng công thức toán học → viết công thức.
>  Nếu dùng model → mô tả kiến trúc và cách train. 


### 7.5 Cách train và lưu model (nếu dùng ML)
```
Cần trả lời:
- Train trên dữ liệu gì? (mock data? data thật?)
- Train lúc nào? (một lần offline, hay cập nhật định kỳ?)
- Lưu model dạng gì? (.pkl? .joblib?)
- Backend load model như thế nào?
```

### 7.6 Đảm bảo miền giá trị output
```
[ Điểm đầu ra có thể nằm trong khoảng nào?
  Có cơ chế clamp/normalize về [0, 1] hoặc [0, 10] không? ]
```

### 7.7 Xử lý trường hợp dữ liệu chưa đủ
```
[ Nếu quán chưa có đủ session để tính điểm → xử lý thế nào? ]
```

---

## 8. Output Contract

> Định nghĩa chính xác dữ liệu module trả về cho Backend.
> Đây là **giao kèo với backend** — sau khi chốt, backend sẽ code nhận đúng format này.

### 8.1 Format output ở mức session
```python
# Kết quả sau khi xử lý 1 session
```

### 8.2 Format output ở mức quán (dùng cho scoring + export)
```python
# Kết quả tổng hợp theo cafe_id
```

### 8.3 Cách trả kết quả về Backend
```
Cần trả lời:
- Module trả kết quả qua return value của function?
- Hay tự ghi thẳng vào DB?
- Hay trả qua file / queue?
→ Cần chốt với Tech Lead
```

---

## 9. Thư viện và công nghệ


| Thư viện | Mục đích sử dụng | Version dự kiến |
|---|---|---|
| [ ? ] | [ ? ] | [ ? ] |

---

## 10. Kế hoạch kiểm thử


### 10.1 Test với mock data
```
[ Test case nào cần chạy với mock data? Kết quả mong đợi là gì? ]
```

### 10.2 Acceptance criteria
```
[ Thế nào là module hoạt động đúng? Đo bằng gì? ]
Gợi ý từ RA: Precision ≥ 80% khi test thủ công tại quán thật.
```

### 10.3 Edge cases cần test
```
[  ]
```

---

## 11. Câu hỏi mở / Cần quyết định

> Ghi lại những điều chưa chắc chắn, cần hỏi lại Lead hoặc Mentor.

| # | Câu hỏi | Người cần trả lời | Trạng thái |
|---|---|---|---|
| 1 | [ ? ] | [ ? ] | Chưa hỏi |

---

## 12. Ghi chú phiên bản

### v0.1
- Tạo khung template
- Chờ hoàn thiện nội dung
