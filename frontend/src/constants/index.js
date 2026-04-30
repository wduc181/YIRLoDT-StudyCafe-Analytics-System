/**
 * constants/index.js — App-wide Constants.
 * Ref: AGENTS.md mục 4, docs/ui_flow.md mục 7.
 */

// GPS tracking interval: 60 giây — KHÔNG thay đổi giá trị này (AGENTS.md rule 9.3)
export const GPS_TRACKING_INTERVAL_MS = 60000;

// GPS States (docs/ui_flow.md mục 7.1)
export const GPS_STATUS = {
  IDLE: 'idle',
  READY: 'ready',
  TRACKING: 'tracking',
  ERROR: 'error',
};

// Session States (docs/ui_flow.md mục 7.2)
export const SESSION_STATUS = {
  NOT_STARTED: 'not_started',
  ACTIVE: 'active',
  ENDED: 'ended',
};

// Screen Names (docs/ui_flow.md mục 3)
export const SCREENS = {
  HOME: 'home',               // S1
  SESSION_ACTIVE: 'session',   // S2
  RESULT: 'result',            // S3
  CAFE_LIST: 'cafe_list',      // S4
  SUGGEST_CAFE: 'suggest',     // S5 [Optional]
};

// S4 distance filters. Backend accepts any positive radius; UI exposes fixed options.
export const DISTANCE_FILTER_OPTIONS = [
  { value: '5km', label: '5km', radius: 5000 },
  { value: '10km', label: '10km', radius: 10000 },
  { value: 'all', label: 'Tất cả', radius: null },
];

export const DEFAULT_DISTANCE_FILTER = '5km';
