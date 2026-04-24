"""
mock_data.py — Sinh mock data để test pipeline.

Ref: docs/api_design.md mục 5.7.

[AI-6 FIX] Thêm 4 loại session để pipeline được test end-to-end thực sự:

  STUDYING     : GPS sạch, drift nhỏ trong ~5m, accuracy 8-20m, > 20 phút
                 → Pipeline kỳ vọng: is_studying=True
                 → Test: happy path, weighted score cao

  NOISY_GPS    : ~65% điểm accuracy > 50m (nhiễu nặng)
                 → Pipeline kỳ vọng: clean_rate < 0.5, thường is_studying=False
                 → Test: noise filter lớp A, MIN_CLEAN_POINTS guard

  SHORT        : GPS sạch nhưng chỉ 12 phút (< MIN_STABLE_DURATION_MIN=20 phút)
                 → Pipeline kỳ vọng: is_studying=False, reason='too_short'
                 → Test: ngưỡng thời gian tối thiểu, f5_retention=0

  OUTSIDE_CAFE : GPS sạch, ổn định nhưng ~250m về phía Bắc tâm quán
                 (vượt 2×radius=100m → bị geofence; vượt radius+buffer=70m → outside radius)
                 → Pipeline kỳ vọng: is_studying=False
                 → Test: không nhầm người ngồi quán bên cạnh

Phân bổ mỗi quán (10 sessions):
  6 × STUDYING | 2 × NOISY_GPS | 1 × SHORT | 1 × OUTSIDE_CAFE
Tổng: 3 quán × 10 sessions = 30 sessions, ~1.600 GPS logs.
"""

import uuid
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cafe import Cafe
from app.models.session import Session
from app.models.gps_log import GpsLog

# ── Seed cố định → kết quả reproducible qua mỗi lần import ──────────────────
_RNG = random.Random(42)

# ── GPS drift constants ───────────────────────────────────────────────────────
_TINY_DRIFT      = 0.000009   # ≈ 1m  — rất ổn định (short/outside sessions)
_SMALL_DRIFT     = 0.000045   # ≈ 5m  — indoor GPS drift bình thường (studying)
_OUTSIDE_OFFSET  = 0.0025     # ≈ 278m về phía Bắc — chắc chắn ngoài radius

# ── Session specs dùng chung cho cả 3 quán ───────────────────────────────────
# (session_type, duration_min, hour_offset)
# hour_offset: căn để sessions không overlap trong DB
_SESSION_SPECS = [
    # 6 × STUDYING — thời gian đa dạng để test nhiều mức feature
    ("studying",      90,  0),
    ("studying",      75,  3),
    ("studying",     120,  6),
    ("studying",      60,  9),
    ("studying",      45, 12),
    ("studying",      50, 15),
    # 2 × NOISY_GPS
    ("noisy_gps",     60, 18),
    ("noisy_gps",     45, 21),
    # 1 × SHORT
    ("short",         12, 24),
    # 1 × OUTSIDE_CAFE
    ("outside_cafe",  60, 27),
]


# ════════════════════════════════════════════════════════════════════════════
# Public entry point
# ════════════════════════════════════════════════════════════════════════════

async def import_mock_data(db: AsyncSession) -> dict:
    """
    Tạo sessions + GPS logs giả lập với đa dạng loại hành vi.
    Trả về số sessions và logs đã import.
    """
    mock_cafes = [
        Cafe(
            name="The Coffee House - Tran Dai Nghia",
            address="68 Tran Dai Nghia, Hai Ba Trung, Ha Noi",
            center_lat=21.0024, center_lng=105.8453,
            radius_meters=50, status="active",
        ),
        Cafe(
            name="Highlands Coffee - Bach Khoa",
            address="1 Giai Phong, Hai Ba Trung, Ha Noi",
            center_lat=21.0035, center_lng=105.8468,
            radius_meters=50, status="active",
        ),
        Cafe(
            name="Phuc Long - Le Thanh Nghi",
            address="42 Le Thanh Nghi, Hai Ba Trung, Ha Noi",
            center_lat=21.0010, center_lng=105.8490,
            radius_meters=50, status="active",
        ),
    ]
    db.add_all(mock_cafes)
    await db.flush()

    total_sessions = 0
    total_logs     = 0
    # Mốc thời gian: 7 ngày trước để không xung đột với data thật
    base_time = datetime.now(timezone.utc) - timedelta(days=7)

    for cafe_idx, cafe in enumerate(mock_cafes):
        cafe_sessions = []
        # Offset theo quán để sessions của các quán không trùng timestamp
        cafe_time_offset = timedelta(hours=cafe_idx * 36)

        for spec_idx, (stype, dur, hour_off) in enumerate(_SESSION_SPECS):
            session_start = base_time + cafe_time_offset + timedelta(hours=hour_off)
            session = Session(
                session_id=uuid.uuid4(),
                device_id=f"mock-{stype[:4]}-{cafe_idx}{spec_idx:02d}",
                cafe_id=cafe.cafe_id,
                start_time=session_start,
                end_time=session_start + timedelta(minutes=dur),
                duration_min=float(dur),
                status="completed",
            )
            db.add(session)
            cafe_sessions.append((session, session_start, dur, stype, cafe))
            total_sessions += 1

        # Flush theo batch cafe trước khi insert GPS logs
        await db.flush()

        for session, start, dur, stype, c in cafe_sessions:
            logs = _make_logs(session.session_id, session.device_id, start, dur, stype, c)
            for log in logs:
                db.add(log)
            total_logs += len(logs)

    await db.commit()
    return {"imported_sessions": total_sessions, "imported_logs": total_logs}


# ════════════════════════════════════════════════════════════════════════════
# GPS log generators
# ════════════════════════════════════════════════════════════════════════════

def _make_logs(session_id, device_id, start, dur, stype, cafe) -> list:
    """Dispatch tới generator phù hợp theo session_type."""
    dispatch = {
        "studying":     _logs_studying,
        "noisy_gps":    _logs_noisy_gps,
        "short":        _logs_short,
        "outside_cafe": _logs_outside_cafe,
    }
    fn = dispatch.get(stype)
    return fn(session_id, device_id, start, dur, cafe) if fn else []


def _make_point(session_id, device_id, lat, lng, acc, ts) -> GpsLog:
    """Helper tạo GpsLog — tránh lặp boilerplate."""
    return GpsLog(
        session_id=session_id,
        device_id=device_id,
        lat=lat,
        lng=lng,
        accuracy_m=acc,
        timestamp=ts,
        is_noise=False,  # scoring engine tự đánh dấu; DB chỉ lưu raw
    )


def _logs_studying(session_id, device_id, start, dur, cafe) -> list:
    """
    STUDYING: 1 điểm/phút, drift ±5m quanh tâm quán, accuracy 8-20m.
    Mô phỏng người ngồi học tại chỗ với GPS indoor drift tự nhiên.
    Pipeline kỳ vọng: is_studying=True, stable_duration_min ≈ dur.
    """
    logs = []
    for i in range(int(dur)):
        logs.append(_make_point(
            session_id, device_id,
            lat=cafe.center_lat + _RNG.uniform(-_SMALL_DRIFT, _SMALL_DRIFT),
            lng=cafe.center_lng + _RNG.uniform(-_SMALL_DRIFT, _SMALL_DRIFT),
            acc=_RNG.uniform(8.0, 20.0),
            ts=start + timedelta(minutes=i),
        ))
    return logs


def _logs_noisy_gps(session_id, device_id, start, dur, cafe) -> list:
    """
    NOISY_GPS: 65% điểm accuracy > 80m (lớp A lọc), 35% điểm sạch.
    Mô phỏng GPS yếu trong toà nhà lớn hoặc tín hiệu bị che khuất.

    Với MIN_CLEAN_POINTS=5 và 65% nhiễu:
      - 60-min session → ~21 điểm sạch → đủ để pass guard nhưng clustering kém
      - 45-min session → ~15 điểm sạch → đủ nhưng rất ít

    Pipeline kỳ vọng: clean_rate < 0.5; is_studying tuỳ duration sau lọc.
    Test target chính: noise filter lớp A hoạt động đúng với accuracy threshold.
    """
    logs = []
    for i in range(int(dur)):
        if _RNG.random() < 0.65:
            # Nhiễu: accuracy cao + GPS jump nhẹ (multipath)
            lat = cafe.center_lat + _RNG.uniform(-0.002, 0.002)
            lng = cafe.center_lng + _RNG.uniform(-0.002, 0.002)
            acc = _RNG.uniform(80.0, 300.0)
        else:
            # Sạch: gần tâm quán, accuracy tốt
            lat = cafe.center_lat + _RNG.uniform(-_SMALL_DRIFT, _SMALL_DRIFT)
            lng = cafe.center_lng + _RNG.uniform(-_SMALL_DRIFT, _SMALL_DRIFT)
            acc = _RNG.uniform(8.0, 20.0)

        logs.append(_make_point(session_id, device_id, lat, lng, acc,
                                ts=start + timedelta(minutes=i)))
    return logs


def _logs_short(session_id, device_id, start, dur, cafe) -> list:
    """
    SHORT: 12 phút, GPS rất sạch và ổn định.
    Mô phỏng người ghé quán mua đồ uống mang đi, không ngồi học.

    Pipeline kỳ vọng: is_studying=False, reason='too_short'
    (total_duration_min=12 < MIN_STABLE_DURATION_MIN=20)
    Test target: guard thời gian tối thiểu, f5_retention=0.
    """
    logs = []
    for i in range(int(dur)):
        logs.append(_make_point(
            session_id, device_id,
            lat=cafe.center_lat + _RNG.uniform(-_TINY_DRIFT, _TINY_DRIFT),
            lng=cafe.center_lng + _RNG.uniform(-_TINY_DRIFT, _TINY_DRIFT),
            acc=_RNG.uniform(8.0, 15.0),
            ts=start + timedelta(minutes=i),
        ))
    return logs


def _logs_outside_cafe(session_id, device_id, start, dur, cafe) -> list:
    """
    OUTSIDE_CAFE: GPS sạch, cluster chặt nhưng tâm cluster ~278m về phía Bắc.

    Tại sao ~278m:
      - radius_meters = 50m → geofence hard rule = 2×50 = 100m
      - 278m >> 100m → toàn bộ điểm bị lớp geofence đánh dấu is_noise=geofence
      - Sau geofence: 0 điểm sạch → insufficient_clean_data guard kích hoạt
      - Kết quả cuối: is_studying=False

    Mô phỏng người ngồi quán bên cạnh mà hệ thống không được tính nhầm.
    Test target: geofence hard rule + outside_cafe_radius condition.
    """
    outside_lat = cafe.center_lat + _OUTSIDE_OFFSET
    outside_lng = cafe.center_lng
    logs = []
    for i in range(int(dur)):
        logs.append(_make_point(
            session_id, device_id,
            lat=outside_lat + _RNG.uniform(-_TINY_DRIFT, _TINY_DRIFT),
            lng=outside_lng + _RNG.uniform(-_TINY_DRIFT, _TINY_DRIFT),
            acc=_RNG.uniform(8.0, 15.0),
            ts=start + timedelta(minutes=i),
        ))
    return logs
