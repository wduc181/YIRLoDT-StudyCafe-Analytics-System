/**
 * GpsStatusBadge.jsx — Badge trạng thái GPS.
 *
 * Ref: docs/ui_flow.md mục 7.1.
 * - idle:     Badge xám "GPS chưa bật"
 * - ready:    Badge xanh "Sẵn sàng"
 * - tracking: Badge xanh nhấp nháy "Đang tracking"
 * - error:    Badge đỏ + message
 */

import { GPS_STATUS } from "../constants";

const STATUS_CONFIG = {
  [GPS_STATUS.IDLE]: {
    label: "GPS chưa bật",
    dotClass: "bg-gps-idle",
    textClass: "text-gray-400",
    animate: false,
  },
  [GPS_STATUS.READY]: {
    label: "Sẵn sàng",
    dotClass: "bg-gps-ready",
    textClass: "text-green-400",
    animate: false,
  },
  [GPS_STATUS.TRACKING]: {
    label: "Đang tracking",
    dotClass: "bg-gps-tracking",
    textClass: "text-green-400",
    animate: true,
  },
  [GPS_STATUS.ERROR]: {
    label: "Lỗi GPS",
    dotClass: "bg-gps-error",
    textClass: "text-red-400",
    animate: false,
  },
};

export default function GpsStatusBadge({ status, errorMessage }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG[GPS_STATUS.IDLE];

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface border border-slate-700">
      <span
        className={`w-2.5 h-2.5 rounded-full ${config.dotClass} ${
          config.animate ? "animate-pulse-gps" : ""
        }`}
      />
      <span className={`text-sm font-medium ${config.textClass}`}>
        {config.label}
      </span>
      {status === GPS_STATUS.ERROR && errorMessage && (
        <span className="text-xs text-red-300 ml-1">— {errorMessage}</span>
      )}
    </div>
  );
}
