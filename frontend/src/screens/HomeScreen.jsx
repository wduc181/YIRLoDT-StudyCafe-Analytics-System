/**
 * HomeScreen.jsx — S1: Home / Tracking Screen.
 *
 * TODO:
 * - Hiển thị tên dự án + mô tả ngắn.
 * - GpsStatusBadge hiển thị trạng thái GPS.
 * - Nút chính "Bắt đầu học" → xin quyền GPS (nếu chưa) → gọi API
 *   POST /api/session/start → chuyển sang S2.
 * - Nút phụ "Xem danh sách quán" → chuyển sang S4.
 * - Xử lý 3 state: loading, success, error.
 * - Nút disabled khi đang loading.
 * - Ref: docs/ui_flow.md mục 5.1.
 */
