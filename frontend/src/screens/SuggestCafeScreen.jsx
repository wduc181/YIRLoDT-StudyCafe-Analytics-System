// [Optional] FR-B8, FR-A7
/**
 * SuggestCafeScreen.jsx — S5: Suggest Cafe Screen [Optional].
 *
 * TODO:
 * - Ô tìm kiếm tên quán → Google Places Autocomplete (trigger >= 3 ký tự).
 * - Google Maps JS SDK được lazy load chỉ khi user mở màn này.
 * - Danh sách gợi ý từ Google.
 * - Preview thông tin quán đã chọn (tên, địa chỉ, tọa độ tự điền).
 * - Nút "Gửi đề xuất" → POST /api/cafes/suggest.
 * - Sau submit thành công → thông báo + tự quay S4 sau 2 giây.
 * - Nút "Huỷ" → quay S4.
 * - Nút disabled khi đang loading.
 * - Phụ thuộc: GOOGLE_PLACES_API_KEY.
 * - Ref: docs/ui_flow.md mục 5.5.
 */
