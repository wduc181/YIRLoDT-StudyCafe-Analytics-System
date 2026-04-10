/**
 * useGps.js — Custom Hook: GPS Tracking Logic.
 *
 * GPS state machine: idle → ready → tracking → error.
 * Interval 60 giây — KHÔNG thay đổi (AGENTS.md rule 9.3).
 * Logic GPS đặt ở đây, không rải trong component.
 * Ref: docs/ui_flow.md mục 7.1.
 */

import { useState, useRef, useCallback } from "react";
import { GPS_STATUS, GPS_TRACKING_INTERVAL_MS } from "../constants";
import { sendGpsLog } from "../services/api";

export default function useGps() {
  const [gpsStatus, setGpsStatus] = useState(GPS_STATUS.IDLE);
  const [gpsCount, setGpsCount] = useState(0);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const watchRef = useRef(null);

  /** Xin quyền GPS từ browser */
  const requestPermission = useCallback(async () => {
    if (!navigator.geolocation) {
      setGpsStatus(GPS_STATUS.ERROR);
      setError("Trình duyệt không hỗ trợ GPS");
      return false;
    }

    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        () => {
          setGpsStatus(GPS_STATUS.READY);
          setError(null);
          resolve(true);
        },
        (err) => {
          setGpsStatus(GPS_STATUS.ERROR);
          setError(
            err.code === 1
              ? "Bạn cần cho phép quyền vị trí để sử dụng ứng dụng"
              : "Không thể lấy vị trí. Vui lòng thử lại."
          );
          resolve(false);
        },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    });
  }, []);

  /** Gửi 1 điểm GPS lên server */
  const sendPosition = useCallback(async (sessionId, deviceId) => {
    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          try {
            await sendGpsLog({
              sessionId,
              deviceId,
              lat: pos.coords.latitude,
              lng: pos.coords.longitude,
              accuracy: pos.coords.accuracy,
              timestamp: new Date().toISOString(),
            });
            setGpsCount((prev) => prev + 1);
            setError(null);
          } catch (err) {
            // GPS gửi lỗi tạm thời → cảnh báo nhẹ, không dừng session
            console.warn("GPS send failed:", err.message);
            setError("Gửi GPS tạm thất bại, sẽ thử lại...");
          }
          resolve();
        },
        (err) => {
          // GPS mất tạm → retry, không dừng session (docs/ui_flow.md mục 5.2)
          console.warn("GPS position error:", err.message);
          setError("GPS tạm mất tín hiệu, đang thử lại...");
          resolve();
        },
        { enableHighAccuracy: true, timeout: 15000 }
      );
    });
  }, []);

  /** Bắt đầu tracking mỗi 60 giây */
  const startTracking = useCallback(
    (sessionId, deviceId) => {
      setGpsStatus(GPS_STATUS.TRACKING);
      setGpsCount(0);
      setError(null);

      // Gửi ngay lần đầu
      sendPosition(sessionId, deviceId);

      // Interval 60 giây
      intervalRef.current = setInterval(() => {
        sendPosition(sessionId, deviceId);
      }, GPS_TRACKING_INTERVAL_MS);
    },
    [sendPosition]
  );

  /** Dừng tracking */
  const stopTracking = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (watchRef.current) {
      navigator.geolocation.clearWatch(watchRef.current);
      watchRef.current = null;
    }
    setGpsStatus(GPS_STATUS.READY);
    setError(null);
  }, []);

  return {
    gpsStatus,
    gpsCount,
    error,
    requestPermission,
    startTracking,
    stopTracking,
  };
}
