"""
mock_data.py — Sinh mock data để test pipeline.

Ref: docs/api_design.md mục 5.7.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cafe import Cafe
from app.models.session import Session
from app.models.gps_log import GpsLog


async def import_mock_data(db: AsyncSession) -> dict:
    """
    Tạo sessions + GPS logs giả lập.
    Trả về số sessions và logs đã import.
    """
    # Reset toàn bộ dữ liệu demo (bao gồm scoring results) để endpoint
    # có thể gọi lại nhiều lần mà không bị nhân bản.
    await db.execute(text(
        "TRUNCATE TABLE session_results, cafe_scores, gps_logs, sessions, cafes "
        "RESTART IDENTITY CASCADE"
    ))

    # Mock cafes (Hà Nội area)
    mock_cafes = [
        Cafe(name="Between Coffee ( Quán Cafe Ở Giữa )",
             address="1B Ngõ 6 Ao Sen, P. Mộ Lao, Hà Đông, Hà Nội 100000, Việt Nam",
             center_lat=20.982359491327195, center_lng=105.78793058834349, radius_meters=30, status="active"),
        Cafe(name="Between Coffee ( Quán Cafe Ở Giữa )",
             address="Số 1G, Khu Dệt, P. Ao Sen, P. Mộ Lao, Hà Đông, Hà Nội, Việt Nam",
             center_lat=20.98298224221269, center_lng=105.78733641988076, radius_meters=30, status="active"),
        Cafe(name="Nhà Lành Art & Coffee",
             address="Nguyễn Văn Lộc, Làng Việt kiều Châu Âu, Hà Đông, Hà Nội, Việt Nam",
             center_lat=20.984158695126112, center_lng=105.7837073256154, radius_meters=30, status="active"),
        # Test location - tọa độ GPS hiện tại
        Cafe(name="Test Location - Your Current GPS",
             address="Hanoi Test Point",
             center_lat=21.5945721, center_lng=105.8420725, radius_meters=30, status="active"),
        Cafe(name="Test Location - Session Exact Match",
             address="Hanoi Session Match Point",
             center_lat=21.5941, center_lng=105.8432, radius_meters=30, status="active"),
    ]
    db.add_all(mock_cafes)
    await db.flush()

    # Mock sessions + GPS logs
    total_sessions = 0
    total_logs = 0
    session_ids: list[str] = []
    base_time = datetime.now(timezone.utc) - timedelta(days=7)

    for cafe in mock_cafes:
        cafe_sessions = []
        for i in range(10):  # 10 sessions per cafe
            session_start = base_time + timedelta(hours=i * 3)
            session_duration_min = 30 + (i * 10) % 120  # 30–120 phút

            session = Session(
                session_id=uuid.uuid4(),
                device_id=f"mock-device-{i % 5:03d}",
                cafe_id=cafe.cafe_id,
                start_time=session_start,
                end_time=session_start + timedelta(minutes=session_duration_min),
                duration_min=float(session_duration_min),
                status="completed",
            )
            db.add(session)
            cafe_sessions.append((session, session_start, session_duration_min))
            session_ids.append(str(session.session_id))
            total_sessions += 1

        # Flush theo batch để đảm bảo sessions tồn tại trước khi insert GPS logs.
        await db.flush()

        for session, session_start, session_duration_min in cafe_sessions:
            # GPS logs mỗi 60 giây
            log_count = session_duration_min  # 1 log / phút
            for j in range(log_count):
                gps_log = GpsLog(
                    session_id=session.session_id,
                    device_id=session.device_id,
                    lat=cafe.center_lat + (j % 3) * 0.00001,  # Nhẹ drift
                    lng=cafe.center_lng + (j % 5) * 0.00001,
                    accuracy_m=10.0 + (j % 10),
                    timestamp=session_start + timedelta(minutes=j),
                    is_noise=False,
                )
                db.add(gps_log)
                total_logs += 1

    await db.commit()

    return {
        "imported_sessions": total_sessions,
        "imported_logs": total_logs,
        "session_ids": session_ids,
    }
