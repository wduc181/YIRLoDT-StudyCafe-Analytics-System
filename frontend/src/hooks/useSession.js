/**
 * useSession.js — Custom Hook: Session Start/End Logic.
 *
 * Mọi API call qua services/api.js.
 * Xử lý đủ 3 state: loading, success, error (AGENTS.md rule 9.3).
 * Ref: docs/api_design.md mục 5.1, 5.3.
 */

import { useState, useCallback } from "react";
import { startSession as apiStart, endSession as apiEnd } from "../services/api";

export default function useSession() {
  const [sessionData, setSessionData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /** Tạo session mới → trả về { session_id, started_at } */
  const startSession = useCallback(async (deviceId, cafeId = null) => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiStart(deviceId, cafeId);
      setSessionData({
        sessionId: data.session_id,
        startedAt: data.started_at,
      });
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /** Kết thúc session → trả về { ended_at, duration_min } */
  const endSession = useCallback(async (sessionId) => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiEnd(sessionId);
      setSessionData((prev) => ({
        ...prev,
        endedAt: data.ended_at,
        durationMin: data.duration_min,
      }));
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /** Reset state về ban đầu */
  const resetSession = useCallback(() => {
    setSessionData(null);
    setLoading(false);
    setError(null);
  }, []);

  return {
    sessionData,
    loading,
    error,
    startSession,
    endSession,
    resetSession,
  };
}
