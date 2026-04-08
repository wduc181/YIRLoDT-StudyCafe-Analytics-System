/**
 * useSession.js — Custom Hook: Session Start/End Logic.
 *
 * TODO:
 * - startSession(deviceId, cafeId?) → gọi api.startSession(),
 *   trả về sessionId, startedAt.
 * - endSession(sessionId) → gọi api.endSession(),
 *   trả về endedAt, durationMin.
 * - Quản lý state: loading, error, sessionData.
 * - Trả về: { sessionData, loading, error, startSession, endSession }.
 * - Mọi API call qua services/api.js.
 */
