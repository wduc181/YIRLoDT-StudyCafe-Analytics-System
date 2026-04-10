/**
 * CafeCard.jsx — Card hiển thị thông tin quán cafe.
 *
 * Ref: docs/ui_flow.md mục 5.4.
 * - Tên quán, địa chỉ ngắn
 * - Khoảng cách (nếu có)
 * - Điểm hành vi hoặc badge "Chưa đủ dữ liệu"
 * - Nút "Mở Maps" → mở Google Maps URL trong tab mới
 */

import formatDistance from "../utils/formatDistance";

export default function CafeCard({ cafe }) {
  const mapsUrl = `https://www.google.com/maps?q=${cafe.center_lat},${cafe.center_lng}`;

  return (
    <div className="bg-surface rounded-xl p-4 border border-slate-700 animate-fade-in">
      {/* Header: Tên + khoảng cách */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-white font-semibold text-base truncate">
            {cafe.name}
          </h3>
          {cafe.address && (
            <p className="text-slate-400 text-sm mt-0.5 truncate">
              {cafe.address}
            </p>
          )}
        </div>
        {cafe.distance_meters != null && (
          <span className="shrink-0 text-sm font-medium text-brand-400 bg-brand-500/10 px-2 py-0.5 rounded-md">
            {formatDistance(cafe.distance_meters)}
          </span>
        )}
      </div>

      {/* Score + Mở Maps */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-700">
        {/* Score badge */}
        {cafe.has_enough_data && cafe.behavior_score != null ? (
          <div className="flex items-center gap-1.5">
            <span className="text-yellow-400">★</span>
            <span className="text-white font-semibold">
              {cafe.behavior_score.toFixed(1)}
            </span>
            <span className="text-slate-400 text-xs">điểm hành vi</span>
          </div>
        ) : (
          <span className="text-slate-500 text-sm italic">
            Chưa đủ dữ liệu
          </span>
        )}

        {/* Nút Mở Maps */}
        <a
          href={mapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-sm font-medium text-brand-400 hover:text-brand-300 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Mở Maps
        </a>
      </div>
    </div>
  );
}
