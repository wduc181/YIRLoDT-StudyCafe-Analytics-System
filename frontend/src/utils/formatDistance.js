/**
 * formatDistance.js — Helper format khoảng cách.
 *
 * Ref: docs/ui_flow.md mục 5.4 (hành vi):
 *   - < 1000m  → "230m"
 *   - >= 1000m → "1.2km"
 */

export default function formatDistance(meters) {
  if (meters == null) return "";
  if (meters < 1000) {
    return `${Math.round(meters)}m`;
  }
  return `${(meters / 1000).toFixed(1)}km`;
}
