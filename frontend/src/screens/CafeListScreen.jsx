/**
 * CafeListScreen.jsx — S4: Cafe List Screen.
 *
 * Hiển thị danh sách quán. Fallback về list tĩnh GET /api/cafes
 * nếu GPS không sẵn sàng (ui_flow.md mục 5.4).
 * AGENTS.md rule 9.3: "Hiển thị SkeletonLoader khi fetch, không để trắng."
 */

import { useEffect } from "react";
import CafeCard from "../components/CafeCard";
import SkeletonLoader from "../components/SkeletonLoader";

export default function CafeListScreen({
  cafes,
  loading,
  error,
  onFetchCafes,
  onGoHome,
}) {
  useEffect(() => {
    onFetchCafes();
  }, [onFetchCafes]);

  return (
    <div className="flex-1 flex flex-col px-5 py-6 animate-fade-in">
      {/* Header */}
      <h2 className="text-lg font-bold text-white mb-4">
        Danh sách quán cafe
      </h2>

      {/* Error + Retry */}
      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm animate-scale-in">
          <p>{error}</p>
          <button
            onClick={onFetchCafes}
            className="mt-2 text-brand-400 font-medium text-sm hover:text-brand-300"
          >
            Thử lại
          </button>
        </div>
      )}

      {/* Content: Skeleton → List → Empty */}
      <div className="flex-1 flex flex-col gap-3">
        {loading ? (
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

      {/* Nút về Home */}
      <button
        id="btn-go-home-from-cafes"
        onClick={onGoHome}
        className="w-full h-11 mt-4 rounded-xl text-slate-300 font-medium text-sm
          border border-slate-700 hover:border-slate-600 hover:bg-surface
          active:scale-[0.98] transition-all"
      >
        Về trang chủ
      </button>
    </div>
  );
}
