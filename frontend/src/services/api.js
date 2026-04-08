/**
 * api.js — Tất cả API call functions.
 *
 * TODO:
 * - API_BASE đọc từ import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
 * - startSession(deviceId, cafeId) → POST /api/session/start
 * - endSession(sessionId) → POST /api/session/end
 * - sendGpsLog(data) → POST /api/tracking
 * - getCafes() → GET /api/cafes
 * - getNearbyCafes(lat, lng, radius?, limit?) → GET /api/cafes/nearby
 * - suggestCafe(data) → POST /api/cafes/suggest [Optional]
 * - getSession(sessionId) → GET /api/session/{sessionId}
 * - exportReport() → GET /api/report/export (download file)
 * - importMockData(source) → POST /api/mock-data/import
 *
 * - AGENTS.md rule 9.3: "Mọi API call đặt trong services/api.js,
 *   component không gọi fetch trực tiếp."
 * - Xử lý error response format: {"status": "error", "message": "..."}.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// TODO: Implement các function ở trên
