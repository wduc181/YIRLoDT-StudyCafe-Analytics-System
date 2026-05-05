/**
 * api.js — Tất cả API call functions.
 *
 * AGENTS.md rule 9.3: "Mọi API call đặt trong services/api.js,
 * component không gọi fetch trực tiếp."
 *
 * Error response format: {"status": "error", "message": "..."}.
 * Ref: docs/api_design.md mục 5.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/**
 * Helper — gọi fetch + parse JSON + xử lý error chuẩn.
 */
async function request(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  // Nếu response không phải JSON (ví dụ file download)
  const contentType = res.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    return res;
  }

  const data = await res.json();

  if (!res.ok) {
    // Backend trả error format: {"status": "error", "message": "..."}
    // hoặc FastAPI validation: {"detail": ...}
    const message = data?.message || data?.detail || `Request failed: ${res.status}`;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }

  return data;
}

// ─── Session ─────────────────────────────────────

/** POST /api/session/start */
export async function startSession(deviceId, cafeId = null) {
  const body = { device_id: deviceId };
  if (cafeId) body.cafe_id = cafeId;
  return request("/api/session/start", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** POST /api/session/end */
export async function endSession(sessionId) {
  return request("/api/session/end", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

/** GET /api/session/{sessionId} */
export async function getSession(sessionId) {
  return request(`/api/session/${sessionId}`);
}

// ─── Tracking ────────────────────────────────────

/** POST /api/tracking */
export async function sendGpsLog(data) {
  return request("/api/tracking", {
    method: "POST",
    body: JSON.stringify({
      device_id: data.deviceId,
      session_id: data.sessionId,
      lat: data.lat,
      lng: data.lng,
      accuracy: data.accuracy || null,
      timestamp: data.timestamp,
    }),
  });
}

// ─── Cafes ───────────────────────────────────────

/** GET /api/cafes */
export async function getCafes({ lat, lng, radius, minRadius, page, limit } = {}) {
  const params = new URLSearchParams();

  if (lat != null && lng != null) {
    params.set("lat", String(lat));
    params.set("lng", String(lng));
  }
  if (radius != null) params.set("radius", String(radius));
  if (minRadius != null) params.set("min_radius", String(minRadius));
  if (page != null) params.set("page", String(page));
  if (limit != null) params.set("limit", String(limit));

  const query = params.toString();
  return request(query ? `/api/cafes?${query}` : "/api/cafes");
}

// ─── Report ──────────────────────────────────────

function filenameFromContentDisposition(header) {
  const match = header?.match(/filename="?([^"]+)"?/i);
  return match?.[1] || "studycafe_report.xlsx";
}

/** GET /api/report/export */
export async function exportReport() {
  const response = await request("/api/report/export");
  const blob = await response.blob();
  const filename = filenameFromContentDisposition(
    response.headers.get("content-disposition")
  );

  return { blob, filename };
}

// ─── Mock Data ───────────────────────────────────

/** POST /api/mock-data/import */
export async function importMockData() {
  return request("/api/mock-data/import", { method: "POST" });
}
