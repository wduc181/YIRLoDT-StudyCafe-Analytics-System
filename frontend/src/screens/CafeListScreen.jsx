/**
 * CafeListScreen.jsx — S4: Cafe List Screen.
 *
 * Hiển thị danh sách quán. Gọi GET /api/cafes với GPS để có khoảng cách;
 * fallback về list tĩnh nếu GPS không sẵn sàng (ui_flow.md mục 5.4).
 * AGENTS.md rule 9.3: "Hiển thị SkeletonLoader khi fetch, không để trắng."
 */

import { useCallback, useEffect, useState } from "react";
import CafeCard from "../components/CafeCard";
import SkeletonLoader from "../components/SkeletonLoader";
import {
  CAFE_LIST_PAGE_SIZE,
  DEFAULT_DISTANCE_FILTER,
  DISTANCE_FILTER_OPTIONS,
} from "../constants";

export default function CafeListScreen({
  cafes,
  pagination,
  loading,
  error,
  onFetchCafes,
  onGetCurrentPosition,
  onExportCafes,
  exporting,
  exportError,
  onGoHome,
  onGoToSuggest,
}) {
  const [selectedFilter, setSelectedFilter] = useState(DEFAULT_DISTANCE_FILTER);
  const [page, setPage] = useState(1);
  const [hasLocation, setHasLocation] = useState(false);
  const [resolvingLocation, setResolvingLocation] = useState(false);
  const isLoading = loading || resolvingLocation;
  const totalPages = pagination?.totalPages ?? 0;
  const pageLabel = totalPages > 0
    ? `Trang ${pagination?.page ?? page} / ${totalPages}`
    : "Trang 0";
  const canGoPrevious = Boolean(pagination?.hasPrevious) && !isLoading;
  const canGoNext = Boolean(pagination?.hasNext) && !isLoading;

  const loadCafes = useCallback(async () => {
    const filter = DISTANCE_FILTER_OPTIONS.find(
      (option) => option.value === selectedFilter
    );
    setResolvingLocation(true);
    const position = await onGetCurrentPosition?.();
    setResolvingLocation(false);

    if (!position) {
      setHasLocation(false);
      await onFetchCafes({ page, limit: CAFE_LIST_PAGE_SIZE });
      return;
    }

    setHasLocation(true);
    await onFetchCafes({
      position,
      radius: filter?.radius ?? null,
      minRadius: filter?.minRadius ?? null,
      page,
      limit: CAFE_LIST_PAGE_SIZE,
    });
  }, [onFetchCafes, onGetCurrentPosition, page, selectedFilter]);

  const handleFilterChange = (nextFilter) => {
    setSelectedFilter(nextFilter);
    setPage(1);
  };

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      loadCafes();
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [loadCafes]);

  return (
    <div className="flex-1 flex flex-col px-5 py-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 mb-4">
        <h2 className="text-lg font-bold text-white">
          Quán gần bạn nhất
        </h2>
        <button
          type="button"
          onClick={onExportCafes}
          disabled={exporting}
          className="shrink-0 h-9 px-3 rounded-lg text-sm font-medium
            text-brand-400 border border-brand-500/40 bg-brand-500/10
            hover:border-brand-400 hover:text-brand-300
            disabled:opacity-60 disabled:cursor-not-allowed transition-all"
        >
          {exporting ? "Đang xuất..." : "Xuất Excel"}
        </button>
      </div>

      {hasLocation && (
        <div className="grid grid-cols-3 gap-2 mb-4">
          {DISTANCE_FILTER_OPTIONS.map((option) => {
            const isActive = selectedFilter === option.value;

            return (
              <button
                key={option.value}
                type="button"
                onClick={() => handleFilterChange(option.value)}
                disabled={isLoading}
                className={`h-10 rounded-lg text-sm font-medium border transition-all
                  disabled:opacity-60 disabled:cursor-not-allowed
                  ${
                    isActive
                      ? "bg-brand-500 text-white border-brand-400"
                      : "bg-surface border-slate-700 text-slate-300 hover:border-slate-500"
                  }`}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      )}

      {/* Error + Retry */}
      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm animate-scale-in">
          <p>{error}</p>
          <button
            onClick={loadCafes}
            className="mt-2 text-brand-400 font-medium text-sm hover:text-brand-300"
          >
            Thử lại
          </button>
        </div>
      )}

      {exportError && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm animate-scale-in">
          {exportError}
        </div>
      )}

      {/* Content: Skeleton → List → Empty */}
      <div className="flex-1 flex flex-col gap-3">
        {isLoading ? (
          <SkeletonLoader count={3} />
        ) : cafes.length > 0 ? (
          cafes.map((cafe) => <CafeCard key={cafe.cafe_id} cafe={cafe} />)
        ) : (
          !error && (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-slate-500 text-sm text-center">
                Chưa có quán nào trong hệ thống.
                <br />
                Hãy import mock data để xem demo.
              </p>
            </div>
          )
        )}
      </div>

      {pagination && (
        <div className="flex items-center justify-between gap-3 mt-4">
          <button
            type="button"
            onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
            disabled={!canGoPrevious}
            className="h-10 px-4 rounded-lg text-sm font-medium border
              bg-surface border-slate-700 text-slate-300 hover:border-slate-500
              disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            Trước
          </button>
          <span className="text-sm text-slate-400">
            {pageLabel}
          </span>
          <button
            type="button"
            onClick={() => setPage((currentPage) => currentPage + 1)}
            disabled={!canGoNext}
            className="h-10 px-4 rounded-lg text-sm font-medium border
              bg-surface border-slate-700 text-slate-300 hover:border-slate-500
              disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            Sau
          </button>
        </div>
      )}

      {/* Nút đề xuất quán mới [Optional] */}
      <button
        type="button"
        onClick={onGoToSuggest}
        className="w-full h-11 mt-4 rounded-xl text-white font-semibold text-sm
          bg-brand-500 hover:bg-brand-400 disabled:opacity-60
          disabled:cursor-not-allowed active:scale-[0.98] transition-all"
      >
        + Đề xuất quán mới
      </button>

      {/* Nút về Home */}
      <button
        type="button"
        id="btn-go-home-from-cafes"
        onClick={onGoHome}
        className="w-full h-11 mt-3 rounded-xl text-slate-300 font-medium text-sm
          border border-slate-700 hover:border-slate-600 hover:bg-surface
          active:scale-[0.98] transition-all"
      >
        Về trang chủ
      </button>
    </div>
  );
}
