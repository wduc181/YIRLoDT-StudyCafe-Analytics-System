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
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /** Fetch danh sách quán. Nếu có GPS, backend trả thêm distance và sort gần đến xa. */
  const fetchCafes = useCallback(
    async ({
      position = null,
      radius = null,
      minRadius = null,
      page = 1,
      limit,
    } = {}) => {
      setLoading(true);
      setError(null);
      try {
        const params = position
          ? {
              lat: position.lat,
              lng: position.lng,
              radius,
              minRadius,
              page,
              limit,
            }
          : { page, limit };
        const data = await getCafes(params);
        setCafes(data.items ?? data);
        setPagination(
          data.items
            ? {
                page: data.page,
                limit: data.limit,
                total: data.total,
                totalPages: data.total_pages,
                hasNext: data.has_next,
                hasPrevious: data.has_previous,
              }
            : null
        );
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return {
    cafes,
    pagination,
    loading,
    error,
    fetchCafes,
  };
}
