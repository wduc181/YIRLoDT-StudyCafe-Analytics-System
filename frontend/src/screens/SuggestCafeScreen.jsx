/**
 * SuggestCafeScreen.jsx — S5: Suggest Cafe Screen [Optional].
 *
 * [Optional] FR-B2: Tính năng đề xuất quán mới qua Google Places.
 * AGENTS.md rule 9.4: "Tính năng [Optional] chỉ implement sau khi
 * các tính năng Core hoàn thành."
 *
 * Hiện tại: Placeholder screen.
 */

// [Optional] FR-B2
export default function SuggestCafeScreen({ onGoBack }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-10 animate-fade-in">
      <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-slate-800 flex items-center justify-center">
        <span className="text-3xl">🚧</span>
      </div>

      <h2 className="text-lg font-bold text-white mb-2">Đề xuất quán mới</h2>
      <p className="text-slate-400 text-sm text-center mb-8 leading-relaxed">
        Tính năng này sẽ được phát triển sau
        <br />
        khi các tính năng Core hoàn thành.
      </p>

      <button
        onClick={onGoBack}
        className="w-full max-w-xs h-11 rounded-xl text-slate-300 font-medium text-sm
          border border-slate-700 hover:border-slate-600 hover:bg-surface
          active:scale-[0.98] transition-all"
      >
        Quay lại
      </button>
    </div>
  );
}
