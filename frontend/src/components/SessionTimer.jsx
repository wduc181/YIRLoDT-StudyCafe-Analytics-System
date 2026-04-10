/**
 * SessionTimer.jsx — Đồng hồ đếm realtime HH:MM:SS.
 *
 * Nhận startTime (ISO string), tăng mỗi giây.
 * Ref: docs/ui_flow.md mục 5.2.
 */

import { useState, useEffect } from "react";

function formatTime(totalSeconds) {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return [h, m, s].map((v) => String(v).padStart(2, "0")).join(":");
}

export default function SessionTimer({ startTime }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!startTime) return;

    const start = new Date(startTime).getTime();

    const tick = () => {
      const now = Date.now();
      setElapsed(Math.floor((now - start) / 1000));
    };

    tick(); // Cập nhật ngay
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [startTime]);

  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-5xl font-bold tracking-wider text-white font-mono">
        {formatTime(elapsed)}
      </span>
      <span className="text-sm text-slate-400">Thời gian phiên học</span>
    </div>
  );
}
