/**
 * SessionActiveScreen.jsx — S2: Session Active Screen.
 *
 * Hiển thị session đang chạy + tracking GPS.
 * Ref: docs/ui_flow.md mục 5.2.
 */

import SessionTimer from "../components/SessionTimer";
import GpsStatusBadge from "../components/GpsStatusBadge";

export default function SessionActiveScreen({
  sessionData,
  gpsStatus,
  gpsCount,
  gpsError,
  currentCafe,
  scoringEligible,
  onEndSession,
  loading,
}) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-10 animate-fade-in">
      {/* Tiêu đề */}
      <div className="mb-2">
        <GpsStatusBadge status={gpsStatus} errorMessage={gpsError} />
      </div>

      <h2 className="text-lg font-semibold text-white mt-4 mb-8">
        Đang theo dõi phiên học
      </h2>

      {/* Vị trí quán hiện tại */}
      <div className="w-full max-w-xs mb-6 px-4 py-3 rounded-lg bg-surface border border-slate-700 text-center">
        {currentCafe ? (
          <>
            <p className="text-xs text-slate-400 mb-1">Vị trí của bạn</p>
            <p className="text-sm font-semibold text-white">{currentCafe.name}</p>
          </>
        ) : scoringEligible === false ? (
          <p className="text-sm text-yellow-300 leading-relaxed">
            Không phát hiện quán trong cơ sở dữ liệu. Dữ liệu tính điểm sẽ không
            được ghi lại, nhưng GPS vẫn tiếp tục được theo dõi.
          </p>
        ) : (
          <p className="text-sm text-slate-400">Đang xác định vị trí quán...</p>
        )}
      </div>

      {/* Đồng hồ HH:MM:SS */}
      <div className="mb-8">
        <SessionTimer startTime={sessionData?.startedAt} />
      </div>

      {/* GPS count */}
      <div className="flex items-center gap-2 mb-6 px-4 py-2 rounded-lg bg-surface border border-slate-700">
        <span className="text-2xl">📍</span>
        <div>
          <span className="text-xl font-bold text-white">{gpsCount}</span>
          <span className="text-slate-400 text-sm ml-1.5">điểm GPS</span>
        </div>
      </div>

      {/* GPS error nhẹ */}
      {gpsError && (
        <div className="mb-4 px-4 py-2 rounded-lg bg-yellow-500/10 border border-yellow-500/30 text-yellow-300 text-sm text-center animate-scale-in">
          ⚠️ {gpsError}
        </div>
      )}

      {/* Gợi ý giữ app mở */}
      <p className="text-slate-500 text-xs text-center mb-8 px-4 leading-relaxed">
        Giữ màn hình sáng để tracking không bị ngắt.
        <br />
        GPS gửi tự động mỗi 60 giây.
      </p>

      {/* Nút kết thúc */}
      <button
        id="btn-end-session"
        onClick={onEndSession}
        disabled={loading}
        className="w-full max-w-xs h-12 rounded-xl bg-red-500/10 border-2 border-red-500/50 text-red-400 font-semibold text-base
          hover:bg-red-500/20 hover:border-red-500/70
          active:scale-[0.98] transition-all
          disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Đang kết thúc...
          </span>
        ) : (
          "Kết thúc"
        )}
      </button>
    </div>
  );
}
