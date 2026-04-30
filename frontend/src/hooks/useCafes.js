/**
 * useCafes.js — Custom Hook: Fetch Cafes / Nearby Cafes.
 *
 * Mọi API call qua services/api.js.
 * Ref: docs/ui_flow.md mục 5.4, docs/api_design.md mục 5.4.
 */

import { useState, useCallback } from "react";
import { getCafes } from "../services/api";

export default function useCafes() {
  const [cafes, setCafes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /** Fetch danh sách quán. Nếu có GPS, backend trả thêm distance và sort gần đến xa. */
  const fetchCafes = useCallback(async ({ position = null, radius = null } = {}) => {
    setLoading(true);
    setError(null);
    try {
      const params = position
        ? { lat: position.lat, lng: position.lng, radius }
        : {};
      const data = await getCafes(params);
      setCafes(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    cafes,
    loading,
    error,
    fetchCafes,
  };
}
