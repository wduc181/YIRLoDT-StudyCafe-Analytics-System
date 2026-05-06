/**
 * useWakeLock.js — Custom Hook: Screen Wake Lock lifecycle.
 *
 * Hook chỉ nhận enabled để dễ test và không phụ thuộc router/screen.
 * Nếu browser không hỗ trợ hoặc request thất bại, app vẫn hoạt động bình thường.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export default function useWakeLock({ enabled = false } = {}) {
  const supported = useMemo(
    () => typeof navigator !== "undefined" && "wakeLock" in navigator,
    []
  );
  const [active, setActive] = useState(false);
  const [error, setError] = useState(null);

  const wakeLockRef = useRef(null);
  const enabledRef = useRef(enabled);
  const mountedRef = useRef(false);

  enabledRef.current = enabled;

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
    };
  }, []);

  const requestWakeLock = useCallback(async () => {
    if (!supported || wakeLockRef.current) return;

    try {
      if (mountedRef.current) setError(null);

      const lock = await navigator.wakeLock.request("screen");

      if (!mountedRef.current || !enabledRef.current) {
        await lock.release();
        return;
      }

      wakeLockRef.current = lock;
      setActive(true);

      lock.addEventListener("release", () => {
        if (wakeLockRef.current === lock) {
          wakeLockRef.current = null;
          if (mountedRef.current) setActive(false);
        }
      });
    } catch (err) {
      console.warn("Wake Lock request failed:", err);
      if (mountedRef.current) {
        setError(err);
        setActive(false);
      }
    }
  }, [supported]);

  const releaseWakeLock = useCallback(async () => {
    const lock = wakeLockRef.current;
    if (!lock) return;

    wakeLockRef.current = null;

    try {
      await lock.release();
    } catch (err) {
      console.warn("Wake Lock release failed:", err);
      if (mountedRef.current) setError(err);
    } finally {
      if (mountedRef.current) setActive(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) {
      releaseWakeLock();
      return undefined;
    }

    requestWakeLock();

    return () => {
      releaseWakeLock();
    };
  }, [enabled, releaseWakeLock, requestWakeLock]);

  useEffect(() => {
    if (typeof document === "undefined") return undefined;

    const handleVisibilityChange = () => {
      if (
        enabled &&
        document.visibilityState === "visible" &&
        !wakeLockRef.current
      ) {
        requestWakeLock();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [enabled, requestWakeLock]);

  return { supported, active, error };
}
