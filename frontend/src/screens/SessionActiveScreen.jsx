/**
 * SessionActiveScreen.jsx — S2: Session Active Screen.
 *
 * TODO:
 * - Hiển thị "Đang theo dõi phiên học".
 * - SessionTimer đếm thời gian real-time.
 * - Số điểm GPS đã ghi nhận (cập nhật mỗi 60 giây).
 * - GpsStatusBadge trạng thái tracking.
 * - Gợi ý giữ app mở.
 * - Nút "Kết thúc" → gọi POST /api/session/end → chuyển sang S3.
 * - GPS tracking gửi định kỳ 60 giây qua useGps hook.
 * - Nếu GPS mất tạm → cảnh báo nhẹ, không crash.
 * - Nút disabled khi đang loading.
 * - Ref: docs/ui_flow.md mục 5.2.
 */
