/**
 * HomeScreen.jsx — S1: Home / Tracking Screen.
 *
 * Màn hình vào đầu tiên. Bắt đầu session.
 * Ref: docs/ui_flow.md mục 5.1.
 */

import GpsStatusBadge from "../components/GpsStatusBadge";

export default function HomeScreen({
  gpsStatus,
  gpsError,
  onRequestGps,
  onStartSession,
  onGoToCafes,
  loading,
  error,
}) {
  const handleStart = async () => {
    // Nếu GPS chưa được cấp quyền → xin quyền trước
    if (gpsStatus === "idle") {
      const granted = await onRequestGps();
      if (!granted) return;
    }
    onStartSession();
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-10 animate-fade-in">
      {/* Brand Header */}
      <div className="mb-10 text-center">
        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-lg shadow-brand-500/25">
          <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-white">StudyCafe Analytics</h1>
        <p className="text-slate-400 mt-2 text-sm leading-relaxed">
          Đánh giá quán học tập<br />qua hành vi GPS thực tế
        </p>
      </div>

      {/* GPS Status Badge */}
      <div className="mb-8">
        <GpsStatusBadge status={gpsStatus} errorMessage={gpsError} />
      </div>

      {/* Error toast */}
      {error && (
        <div className="mb-4 w-full max-w-xs px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm text-center animate-scale-in">
          {error}
        </div>
      )}

      {/* Nút chính: Bắt đầu học */}
      <button
        id="btn-start-session"
        onClick={handleStart}
        disabled={loading}
        className="w-full max-w-xs h-12 rounded-xl bg-gradient-to-r from-brand-500 to-brand-600 text-white font-semibold text-base
          shadow-lg shadow-brand-500/25 hover:shadow-brand-500/40
          active:scale-[0.98] transition-all
          disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Đang xử lý...
          </span>
        ) : (
          "Bắt đầu học"
        )}
      </button>

      {/* Nút phụ: Xem danh sách quán */}
      <button
        id="btn-go-to-cafes"
        onClick={onGoToCafes}
        className="w-full max-w-xs h-11 mt-3 rounded-xl text-slate-300 font-medium text-sm
          border border-slate-700 hover:border-slate-600 hover:bg-surface
          active:scale-[0.98] transition-all"
      >
        Xem danh sách quán
      </button>
    </div>
  );
}
