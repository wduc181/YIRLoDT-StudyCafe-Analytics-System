/**
 * ResultScreen.jsx — S3: Result / Summary Screen.
 *
 * Xác nhận session đã kết thúc, hiển thị tóm tắt.
 * Ref: docs/ui_flow.md mục 5.3.
 */

export default function ResultScreen({
  sessionData,
  gpsCount,
  onGoHome,
  onGoToCafes,
}) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-10 animate-fade-in">
      {/* Biểu tượng thành công */}
      <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-green-500/10 border-2 border-green-500/30 flex items-center justify-center">
        <svg className="w-10 h-10 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </div>

      <h2 className="text-xl font-bold text-white mb-2">
        Phiên học đã kết thúc
      </h2>
      <p className="text-slate-400 text-sm mb-8">
        Dữ liệu đã được ghi nhận
      </p>

      {/* Thống kê */}
      <div className="w-full max-w-xs flex gap-3 mb-8">
        {/* Thời gian */}
        <div className="flex-1 bg-surface rounded-xl p-4 border border-slate-700 text-center">
          <div className="text-2xl font-bold text-white">
            {sessionData?.durationMin != null
              ? Math.round(sessionData.durationMin)
              : "—"}
          </div>
          <div className="text-xs text-slate-400 mt-1">phút</div>
        </div>

        {/* GPS logs */}
        <div className="flex-1 bg-surface rounded-xl p-4 border border-slate-700 text-center">
          <div className="text-2xl font-bold text-white">{gpsCount}</div>
          <div className="text-xs text-slate-400 mt-1">điểm GPS</div>
        </div>
      </div>

      {/* Nút về Home */}
      <button
        id="btn-go-home"
        onClick={onGoHome}
        className="w-full max-w-xs h-12 rounded-xl bg-gradient-to-r from-brand-500 to-brand-600 text-white font-semibold text-base
          shadow-lg shadow-brand-500/25 hover:shadow-brand-500/40
          active:scale-[0.98] transition-all"
      >
        Về trang chủ
      </button>

      {/* Nút xem danh sách quán */}
      <button
        id="btn-go-to-cafes-result"
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
