/**
 * CafeListScreen.jsx — S4: Cafe List Screen.
 *
 * TODO:
 * - Lấy GPS hiện tại → gọi GET /api/cafes/nearby?lat=...&lng=...
 * - Nếu GPS không sẵn sàng → fallback GET /api/cafes (list tĩnh,
 *   không hiển thị khoảng cách).
 * - Dùng SkeletonLoader khi đang fetch.
 * - Render danh sách CafeCard, sort theo khoảng cách.
 * - Nút "Về trang chủ" → S1.
 * - Nút "+ Đề xuất quán mới" → S5 [Optional].
 * - Xử lý error state: thông báo lỗi + nút "Thử lại".
 * - Ref: docs/ui_flow.md mục 5.4.
 */
