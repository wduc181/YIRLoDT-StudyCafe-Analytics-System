# Project Review — StudyCafe Analytics System

**Ngày review:** 02/05/2026  
**Branch hiện tại:** `fix/pre-demo-findings` (3 commits ahead of `main`)  
**Reviewer:** Coding Agent

---

## Tổng quan

Dự án ở trạng thái khá tốt — kiến trúc rõ ràng, tuân thủ AGENTS.md, docs đồng bộ, scoring engine đã tích hợp. Dưới đây là các findings theo mức độ nghiêm trọng.

---

## 1. BUGs — Cần sửa trước demo

### F-01. `CafeCard.jsx` tự build Google Maps URL, bỏ qua `google_maps_url` từ backend

**File:** [CafeCard.jsx](file:///home/wuudes/projects/%5BYIRLoDT%5D%20StudyCafe%20Analytics%20System/frontend/src/components/CafeCard.jsx#L14)

```jsx
// CafeCard.jsx dòng 14 — tự nối URL
const mapsUrl = `https://www.google.com/maps?q=${cafe.center_lat},${cafe.center_lng}`;
```

Backend đã trả `google_maps_url` trong `CafeResponse`, nhưng frontend tự tạo URL trùng lặp thay vì sử dụng giá trị từ response. Nếu sau này backend thay đổi format URL (ví dụ dùng `google_place_id`), frontend sẽ bị lệch.

> **Fix:** Đổi thành `const mapsUrl = cafe.google_maps_url;`

---

### F-02. `NEARBY_CAFES_DEFAULT_LIMIT` trong config = 5, nhưng router dùng mặc định = 20

**Files:**
- [config.py](file:///home/wuudes/projects/%5BYIRLoDT%5D%20StudyCafe%20Analytics%20System/backend/app/core/config.py#L26): `NEARBY_CAFES_DEFAULT_LIMIT: int = 5`
- [cafes.py router](file:///home/wuudes/projects/%5BYIRLoDT%5D%20StudyCafe%20Analytics%20System/backend/app/routers/cafes.py#L21): `limit: int = Query(default=20, ge=1, le=50)`

Config nói mặc định 5 quán, nhưng router hardcode 20. Theo AGENTS.md rule 9.2: *"Không hardcode giá trị config"*.

> **Fix:** Router nên đọc `settings.NEARBY_CAFES_DEFAULT_LIMIT` hoặc đồng bộ config lên 20 theo `api_design.md` mục 5.4 (ghi limit mặc định 20).

---

### F-03. `App.css` chứa CSS thừa từ Vite template ban đầu

**File:** [App.css](file:///home/wuudes/projects/%5BYIRLoDT%5D%20StudyCafe%20Analytics%20System/frontend/src/App.css)

Toàn bộ 185 dòng CSS (`.counter`, `.hero`, `#center`, `#next-steps`, `#docs`, `#spacer`, `.ticks`) là CSS gốc từ Vite scaffold template — không liên quan đến ứng dụng StudyCafe và **không được import ở đâu trong code hiện tại**. File tăng bundle size vô ích.

> **Fix:** Xóa file hoặc thay bằng nội dung trống. Kiểm tra không file nào import nó.

---

### F-04. `mock_data.py` — TRUNCATE CASCADE xóa sạch bảng `cafe_scores` và `session_results`

**File:** [mock_data.py](file:///home/wuudes/projects/%5BYIRLoDT%5D%20StudyCafe%20Analytics%20System/backend/app/internal/mock_data.py#L24)

```python
await db.execute(text("TRUNCATE TABLE gps_logs, sessions, cafes RESTART IDENTITY CASCADE"))
```

`CASCADE` khiến `cafe_scores` và `session_results` (FK → `cafes`, `sessions`) cũng bị TRUNCATE. Đây có thể là hành vi mong muốn cho demo reset, nhưng **không nói rõ trong comment** và có thể gây mất dữ liệu bất ngờ nếu user nghĩ chỉ reset mock data.

> **Fix:** Thêm `cafe_scores` và `session_results` vào TRUNCATE statement tường minh:
> ```python
> await db.execute(text(
>     "TRUNCATE TABLE session_results, cafe_scores, gps_logs, sessions, cafes "
>     "RESTART IDENTITY CASCADE"
> ))
> ```

---

### F-05. `geo_resolver.py` — Indentation không nhất quán (2 spaces thay vì 4)

**File:** [geo_resolver.py](file:///home/wuudes/projects/%5BYIRLoDT%5D%20StudyCafe%20Analytics%20System/backend/app/internal/geo_resolver.py#L20-L37)

Toàn bộ function body dùng **2-space indent** thay vì 4-space theo chuẩn Python/PEP 8 và phần còn lại của codebase. Không gây lỗi runtime nhưng vi phạm tính nhất quán.

> **Fix:** Reformat sang 4-space indent.

---

## 2. INCONSISTENCIES — Lệch giữa code và docs

### F-06. `api_design.md` mục 5.7 yêu cầu request body `{"source": "mock_dataset_v1"}`, nhưng code không nhận request body

**Docs:** `api_design.md` dòng 312-316 — POST `/api/mock-data/import` có request body `source`  
**Code:** [admin.py router](file:///home/wuudes/projects/%5BYIRLoDT%5D%20StudyCafe%20Analytics%20System/backend/app/routers/admin.py#L17-L23) — chỉ nhận `BackgroundTasks` và `db`, không parse request body

Tuy không gây lỗi (API vẫn chạy khi gọi POST không body), nhưng vi phạm contract.

> **Fix:** Hoặc thêm optional `source` param vào endpoint (theo docs), hoặc cập nhật `api_design.md` bỏ request body.

---

### F-07. `RequirementAnalysis.md` nói file tên `RequirementAnalysis.md` nhưng file thực tế tên `requirement_analysis.md`

**AGENTS.md:** Tham chiếu `docs/RequirementAnalysis.md` (PascalCase)  
**File thực tế:** `docs/requirement_analysis.md` (snake_case)

Không ảnh hưởng runtime nhưng gây nhầm lẫn khi đọc tài liệu.

> **Fix:** Cập nhật AGENTS.md mục 1 thay `RequirementAnalysis.md` → `requirement_analysis.md`.

---

### F-08. `CafeCard.jsx` dùng Google Maps URL trực tiếp, nhưng `api_design.md` mục 5.4 nói backend cũng có thể trả URL dạng directions

**Docs:** Backend có thể dùng URL dạng `https://www.google.com/maps/dir/?api=1&destination=...`  
**Code:** Backend chỉ dùng URL dạng `https://www.google.com/maps?q=...`

Hiện tại không phải bug nhưng nếu sau này thêm directions URL thì cần sửa cả backend `cafe_service._google_maps_url()`.

---

## 3. CODE QUALITY — Cải thiện

### F-09. `App.jsx` — `DEVICE_ID` được tạo mới mỗi lần module reload (HMR trong dev)

**File:** [App.jsx](file:///home/wuudes/projects/%5BYIRLoDT%5D%20StudyCafe%20Analytics%20System/frontend/src/App.jsx#L24-L28)

```jsx
function getDeviceId() {
  return "device-" + Math.random().toString(36).substr(2, 9);
}
const DEVICE_ID = getDeviceId();
```

Trong dev mode với Vite HMR, mỗi lần save file sẽ tạo `DEVICE_ID` mới → session gửi GPS với `device_id` khác nhau. Tuy AGENTS.md nói không dùng localStorage, nhưng `DEVICE_ID` nên ổn định trong 1 tab.

> **Fix:** Dùng `useRef` trong component hoặc `useState` với lazy init để đảm bảo device_id không đổi trong cùng 1 mount lifecycle. Hoặc chấp nhận vì demo scope nhỏ.

---

### F-10. `scoring_service._get_cafe_history()` — Query `AVG(CafeScore.behavior_score)` tính trên TẤT CẢ bản ghi, không chỉ bản mới nhất mỗi quán

**File:** [scoring_service.py](file:///home/wuudes/projects/%5BYIRLoDT%5D%20StudyCafe%20Analytics%20System/backend/app/services/scoring_service.py#L147-L152)

```python
avg_stmt = (
    select(func.avg(CafeScore.behavior_score))
    .where(CafeScore.has_enough_data.is_(True))
)
```

`cafe_scores` là **append-only** (mỗi lần tính tạo bản ghi mới). Query này tính AVG trên tất cả bản ghi lịch sử, bao gồm cả bản ghi cũ → `system_avg_score` bị distort bởi lịch sử.

> **Fix:** Chỉ lấy AVG từ bản ghi MỚI NHẤT (latest computed_at) mỗi quán:
> ```python
> # Dùng subquery lấy max computed_at per cafe_id trước khi tính avg
> ```

---

### F-11. `mock_data.py` — indentation không nhất quán cho 2 cafe cuối

**File:** [mock_data.py](file:///home/wuudes/projects/%5BYIRLoDT%5D%20StudyCafe%20Analytics%20System/backend/app/internal/mock_data.py#L41-L43)

```python
           Cafe(name="Test Location - Session Exact Match",
               address="Hanoi Session Match Point",
               center_lat=21.5941, center_lng=105.8432, radius_meters=30, status="active"),
```

Dòng 41-43 bị thụt lệch so với các Cafe khác ở dòng 28-40 (thừa spaces). Không gây lỗi nhưng vi phạm code style.

---

### F-12. `CafeListScreen.jsx` — `loadCafes()` chạy trong `useEffect` với `setTimeout(0)`, gây re-fetch khi `selectedFilter` thay đổi

**File:** [CafeListScreen.jsx](file:///home/wuudes/projects/%5BYIRLoDT%5D%20StudyCafe%20Analytics%20System/frontend/src/screens/CafeListScreen.jsx#L52-L58)

`loadCafes` nằm trong dependency array của `useEffect`, và `loadCafes` phụ thuộc vào `selectedFilter`. Khi user chọn filter mới → `loadCafes` tạo mới → useEffect re-run → fetch lại. Behaviour này **đúng ý đồ**, nhưng `setTimeout(0)` không cần thiết và có thể gây double-fetch trong StrictMode.

> **Suggestion:** Bỏ `setTimeout`, gọi `loadCafes()` trực tiếp. Hoặc thêm comment giải thích lý do dùng setTimeout.

---

## 4. MISSING IMPLEMENTATIONS

### F-13. Optional endpoints chưa implement (đúng AGENTS.md rule 9.4)

Các endpoint Optional đã được stub đúng quy trình:
- `POST /api/cafes/suggest` — stub comment ở [cafes.py:50](file:///home/wuudes/projects/%5BYIRLoDT%5D%20StudyCafe%20Analytics%20System/backend/app/routers/cafes.py#L50)
- `POST /api/admin/cafes/{cafe_id}/approve` — stub comment ở [admin.py:37](file:///home/wuudes/projects/%5BYIRLoDT%5D%20StudyCafe%20Analytics%20System/backend/app/routers/admin.py#L37)
- `SuggestCafeScreen.jsx` — placeholder đúng

> **Status:** OK theo AGENTS.md rule 9.4. Không phải lỗi.

---

### F-14. Chưa có Alembic migrations

`requirements.txt` include `alembic` nhưng không có thư mục `alembic/` hay `alembic.ini`. Hiện dùng `Base.metadata.create_all` (dev-only). Nếu DB schema thay đổi, cần migration.

> **Status:** Chấp nhận được cho demo. Flag nếu cần deploy production.

---

## 5. INFRASTRUCTURE & CONFIG

### F-15. Docker Compose — backend expose port 8088, nhưng frontend VITE_API_BASE_URL trỏ localhost:8088

**File:** [docker-compose.yml](file:///home/wuudes/projects/%5BYIRLoDT%5D%20StudyCafe%20Analytics%20System/docker-compose.yml#L34-L65)

```yaml
backend:
  ports: "8088:8000"
frontend:
  environment:
    VITE_API_BASE_URL: "http://localhost:8088"
```

Đây là **build-time env** cho Vite. Khi chạy frontend container, VITE build đã embed URL lúc build → nếu build trong Docker network, `localhost:8088` chỉ đúng khi truy cập từ host browser, không phải từ container.

Hiện tại chạy được vì frontend volume mount + dev server, nhưng nếu build production image sẽ cần chú ý.

> **Status:** OK cho dev workflow hiện tại.

---

### F-16. `.env` đang bị commit vào git

**File:** `.env` (446 bytes) nằm trong repo. Tuy chỉ chứa credentials local/dev, nhưng AGENTS.md nói `.env` không commit.

> **Check:** Xác nhận `.gitignore` có `.env`:

Kiểm tra `.gitignore` thấy đã có `.env` → file có thể đã được tracked trước khi add vào `.gitignore`.

> **Fix:** `git rm --cached .env` rồi commit.

---

## 6. TESTING

### F-17. Test files tồn tại nhưng coverage hạn chế

**Files trong `backend/tests/`:**
- `test_api_contract.py` (3.3KB)
- `test_cafe_service.py` (2.4KB)
- `test_session_service.py` (2.7KB)
- `test_tracking_service.py` (5.0KB)
- `test_haversine.py` (257B)

> **Observation:** Không có test cho `report_service`, `scoring_service`, `mock_data`. Scoring engine có thư mục test riêng (`scoring_engine/tests/`). Có thể chấp nhận cho demo scope.

---

## 7. Tóm tắt theo mức độ ưu tiên

| Priority | ID | Mô tả | Effort |
|---|---|---|---|
| **P0 — Bug** | F-01 | CafeCard không dùng `google_maps_url` từ backend | 1 dòng |
| **P0 — Bug** | F-02 | Limit config lệch giữa `config.py` (5) và router (20) | 1 dòng |
| **P1 — Quality** | F-03 | Xóa `App.css` thừa từ Vite template | Delete file |
| **P1 — Quality** | F-05 | `geo_resolver.py` indent 2-space | Reformat |
| **P1 — Quality** | F-11 | `mock_data.py` indent lệch | 3 dòng |
| **P1 — Consistency** | F-06 | Mock data endpoint thiếu request body theo contract | Docs hoặc code |
| **P1 — Consistency** | F-07 | Tên file docs lệch AGENTS.md | Đổi tên hoặc sửa ref |
| **P2 — Data** | F-10 | `system_avg_score` tính trên toàn bộ history thay vì latest | Query refactor |
| **P2 — Data** | F-04 | TRUNCATE CASCADE cần comment rõ hoặc liệt kê tường minh | Sửa SQL |
| **P2 — Quality** | F-09 | Device ID thay đổi khi HMR | Minor refactor |
| **P2 — Quality** | F-12 | setTimeout(0) không cần thiết trong CafeListScreen | 3 dòng |
| **P3 — Ops** | F-16 | `.env` đang tracked trong git | `git rm --cached` |
| **P3 — Info** | F-14 | Chưa có Alembic migrations | Chấp nhận cho demo |

---

## 8. Kết luận xác minh của coding agent

Đã đối chiếu lại các findings với codebase hiện tại trên branch `fix/pre-demo-findings`.
Kết luận tổng quan: phần lớn findings là đúng, nhưng một số mục cần hạ mức hoặc
chỉnh lại diễn giải để tránh sửa nhầm.

| ID | Kết luận | Ghi chú |
|---|---|---|
| F-01 | Đúng | `CafeCard.jsx` tự build Google Maps URL thay vì dùng `cafe.google_maps_url` từ backend. Nên sửa. |
| F-02 | Đúng | `NEARBY_CAFES_DEFAULT_LIMIT` trong config là 5, còn router/service/docs API dùng mặc định 20. Nên chốt theo `api_design.md` là 20 hoặc dùng config thống nhất. |
| F-03 | Đúng một phần | `App.css` là CSS scaffold và không được import. Vì không import nên không làm tăng bundle size, nhưng vẫn nên xóa để sạch repo. |
| F-04 | Đúng | `TRUNCATE ... CASCADE` có thể xóa `cafe_scores` và `session_results`. Nên liệt kê bảng tường minh hoặc comment rõ đây là reset demo. |
| F-05 | Đúng | `geo_resolver.py` dùng indent 2 spaces, lệch style Python/codebase. |
| F-06 | Đúng | `api_design.md` yêu cầu body `source`, nhưng `/api/mock-data/import` không nhận request body. Đây là contract drift. |
| F-07 | Đúng | `AGENTS.md` và `README.md` trỏ `docs/RequirementAnalysis.md`, file thật là `docs/requirement_analysis.md`. |
| F-08 | Đúng một phần | Docs cho phép cả URL dạng `q=` và `dir/?destination=...`; backend đang dùng `q=` nên không sai contract. Vấn đề chính là F-01: frontend nên dùng URL backend trả. |
| F-09 | Đúng | `DEVICE_ID` tạo ở module scope có thể đổi khi Vite HMR reload module. Minor dev/demo risk. |
| F-10 | Đúng | `system_avg_score` đang tính trên toàn bộ lịch sử `CafeScore`, trong khi score là append-only. Tuy nhiên mục này chạm scoring behavior nên cần cẩn trọng theo scoring boundary rule. |
| F-11 | Đúng | `mock_data.py` có indent lệch ở cafe cuối. |
| F-12 | Đúng một phần | `setTimeout(0)` trong `CafeListScreen.jsx` không cần thiết. Re-fetch khi filter đổi là đúng ý đồ; double-fetch không chắc chắn, nhưng nên bỏ timeout. |
| F-13 | Đúng, không phải lỗi | Optional stubs đang đúng với AGENTS.md rule 9.4. |
| F-14 | Đúng | Có dependency Alembic nhưng chưa có `alembic.ini`/migration folder. Chấp nhận cho demo, cần nếu production. |
| F-15 | Đúng theo ngữ cảnh dev | Docker hiện chạy Vite dev server; browser host gọi `localhost:8088` là hợp lý. Chỉ cần lưu ý nếu làm production image. |
| F-16 | Sai | `.env` tồn tại local nhưng không tracked trong git. `git ls-files .env` không trả output; chỉ `.env.example` và `.gitignore` tracked. Không cần `git rm --cached .env`. |
| F-17 | Đúng | Test coverage còn hạn chế, nhất là `report_service`, `mock_data`, và một phần backend integration. Scoring engine có test riêng. |

### Ưu tiên sửa đề xuất

Sửa trước: F-01, F-02, F-06, F-04, F-05/F-11, F-07.

Để sau hoặc cần xác nhận thêm: F-10 vì liên quan scoring behavior; F-14/F-15 vì
thuộc phase infra/production sau demo.

Bỏ khỏi danh sách sửa: F-16.
