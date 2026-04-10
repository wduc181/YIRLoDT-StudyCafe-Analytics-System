/**
 * SkeletonLoader.jsx — Loading placeholder animated.
 *
 * Hiển thị shimmer animation khi fetch danh sách quán.
 * AGENTS.md rule 9.3: "Hiển thị SkeletonLoader khi fetch danh sách quán,
 * không để màn hình trắng."
 * Ref: docs/ui_flow.md mục 7.3.
 */

export default function SkeletonLoader({ count = 3 }) {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="bg-surface rounded-xl p-4 border border-slate-700"
        >
          {/* Tên quán skeleton */}
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="h-5 w-3/4 rounded animate-shimmer" />
              <div className="h-4 w-1/2 rounded mt-2 animate-shimmer" />
            </div>
            <div className="h-6 w-12 rounded animate-shimmer" />
          </div>

          {/* Score + button skeleton */}
          <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-700">
            <div className="h-4 w-24 rounded animate-shimmer" />
            <div className="h-4 w-20 rounded animate-shimmer" />
          </div>
        </div>
      ))}
    </div>
  );
}
