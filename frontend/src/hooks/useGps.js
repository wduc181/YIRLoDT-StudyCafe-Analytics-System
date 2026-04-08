/**
 * useGps.js — Custom Hook: GPS Tracking Logic.
 *
 * TODO:
 * - Quản lý GPS state: idle → ready → tracking → error.
 * - requestPermission() → xin quyền GPS từ browser.
 * - startTracking(sessionId) → bắt đầu gửi GPS mỗi 60 giây
 *   qua POST /api/tracking (dùng services/api.js).
 * - stopTracking() → dừng interval.
 * - Trả về: { gpsStatus, gpsCount, error, requestPermission,
 *   startTracking, stopTracking }.
 * - GPS tracking interval: 60 giây — KHÔNG thay đổi giá trị này.
 * - Xử lý GPS mất tạm: retry, không dừng session.
 * - AGENTS.md rule 9.3: Logic GPS đặt ở đây, không rải trong component.
 */
