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
        # ===== Quán gốc (giữ nguyên) =====
        Cafe(name="Between Coffee ( Quán Cafe Ở Giữa )",
             address="1B Ngõ 6 Ao Sen, P. Mộ Lao, Hà Đông, Hà Nội 100000, Việt Nam",
             center_lat=20.982359491327195, center_lng=105.78793058834349, radius_meters=50, status="active"),
        Cafe(name="Between Coffee ( Quán Cafe Ở Giữa )",
             address="Số 1G, Khu Dệt, P. Ao Sen, P. Mộ Lao, Hà Đông, Hà Nội, Việt Nam",
             center_lat=20.98298224221269, center_lng=105.78733641988076, radius_meters=50, status="active"),
        Cafe(name="Nhà Lành Art & Coffee",
             address="Nguyễn Văn Lộc, Làng Việt kiều Châu Âu, Hà Đông, Hà Nội, Việt Nam",
             center_lat=20.984158695126112, center_lng=105.7837073256154, radius_meters=50, status="active"),

        # ===== Hoàn Kiếm =====
        Cafe(name="Cafe Giang",
             address="39 Nguyễn Hữu Huân, Lý Thái Tổ, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.033967, center_lng=105.852432, radius_meters=50, status="active"),
        Cafe(name="The Note Coffee",
             address="64 Lương Văn Can, Hàng Trống, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.029612, center_lng=105.849573, radius_meters=50, status="active"),
        Cafe(name="Cafe Nola",
             address="89 Mã Mây, Hàng Buồm, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.035011, center_lng=105.851845, radius_meters=50, status="active"),
        Cafe(name="Tranquil Books & Coffee",
             address="5 Nguyễn Quang Bích, Cửa Đông, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.033124, center_lng=105.846012, radius_meters=50, status="active"),
        Cafe(name="Loading T Cafe",
             address="8 Chân Cầm, Hàng Trống, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.030782, center_lng=105.848251, radius_meters=50, status="active"),
        Cafe(name="Hanoi House Cafe",
             address="47 Lý Quốc Sư, Hàng Trống, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.030645, center_lng=105.847982, radius_meters=50, status="active"),
        Cafe(name="Hoa 10 Giờ Cafe",
             address="26 Hàng Vôi, Lý Thái Tổ, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.031845, center_lng=105.852641, radius_meters=50, status="active"),
        Cafe(name="Hidden Gem Coffee",
             address="1 Hàng Mắm, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.033501, center_lng=105.854123, radius_meters=50, status="active"),
        Cafe(name="Lofita Cafe",
             address="12-14 Ấu Triệu, Hàng Trống, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.029823, center_lng=105.848742, radius_meters=50, status="active"),
        Cafe(name="Cafe Lâm",
             address="60 Nguyễn Hữu Huân, Lý Thái Tổ, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.034101, center_lng=105.852895, radius_meters=50, status="active"),
        Cafe(name="Maison Marou",
             address="91A Thợ Nhuộm, Trần Hưng Đạo, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.023561, center_lng=105.847832, radius_meters=50, status="active"),
        Cafe(name="The Coffee House Hoàn Kiếm",
             address="37 Quang Trung, Trần Hưng Đạo, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.023012, center_lng=105.849512, radius_meters=50, status="active"),
        Cafe(name="Cộng Cà Phê Đinh Tiên Hoàng",
             address="16 Đinh Tiên Hoàng, Lý Thái Tổ, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.028923, center_lng=105.854012, radius_meters=50, status="active"),
        Cafe(name="Phúc Long Hoàn Kiếm",
             address="23 Đinh Tiên Hoàng, Lý Thái Tổ, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.029312, center_lng=105.854612, radius_meters=50, status="active"),
        Cafe(name="Starbucks Hoàn Kiếm",
             address="59 Lý Thái Tổ, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.028712, center_lng=105.853412, radius_meters=50, status="active"),
        Cafe(name="Goc Ha Noi",
             address="11 Hang Gai, Hàng Trống, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.031234, center_lng=105.849912, radius_meters=50, status="active"),
        Cafe(name="The Workshop Coffee",
             address="27 Trần Hưng Đạo, Phan Chu Trinh, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.024512, center_lng=105.849023, radius_meters=50, status="active"),
        Cafe(name="RuNam Nguyễn Hữu Huân",
             address="39 Nguyễn Hữu Huân, Lý Thái Tổ, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.033512, center_lng=105.852012, radius_meters=50, status="active"),
        Cafe(name="Tang Tret Cosmo Cafe",
             address="10 Khúc Hạo, Điện Bàn, Ba Đình, Hà Nội, Việt Nam",
             center_lat=21.044212, center_lng=105.835602, radius_meters=50, status="active"),

        # ===== Tây Hồ =====
        Cafe(name="Aha Café Trích Sài",
             address="217 Trích Sài, Hàng Bưởi, Tây Hồ, Hà Nội, Việt Nam",
             center_lat=21.055423, center_lng=105.820341, radius_meters=50, status="active"),
        Cafe(name="Serein Café & Lounge",
             address="64 Xuân Diệu, Quảng An, Tây Hồ, Hà Nội, Việt Nam",
             center_lat=21.063412, center_lng=105.823451, radius_meters=50, status="active"),
        Cafe(name="Cafe Mai Tây Hồ",
             address="22 Ngõ 185A Trích Sài, Tây Hồ, Hà Nội, Việt Nam",
             center_lat=21.051234, center_lng=105.819823, radius_meters=50, status="active"),
        Cafe(name="Trung Nguyên Legend Tây Hồ",
             address="Lotte Mall Tây Hồ, 272 Võ Chí Công, Phú Thượng, Tây Hồ, Hà Nội, Việt Nam",
             center_lat=21.074512, center_lng=105.812341, radius_meters=50, status="active"),

        # ===== Ba Đình =====
        Cafe(name="Sam Rooftop Coffee",
             address="106 Trấn Vũ, Ba Đình, Hà Nội, Việt Nam",
             center_lat=21.045123, center_lng=105.832901, radius_meters=50, status="active"),
        Cafe(name="Tiny Cafe",
             address="19 Cao Bá Quát, Điện Biên, Ba Đình, Hà Nội, Việt Nam",
             center_lat=21.040234, center_lng=105.838512, radius_meters=50, status="active"),
        Cafe(name="Maison de Tet Decor",
             address="55 Hàng Bún, Quán Thánh, Ba Đình, Hà Nội, Việt Nam",
             center_lat=21.039923, center_lng=105.843512, radius_meters=50, status="active"),
        Cafe(name="King Coffee Ba Đình",
             address="182-184 Quán Thánh, Ba Đình, Hà Nội, Việt Nam",
             center_lat=21.041234, center_lng=105.840123, radius_meters=50, status="active"),
        Cafe(name="De.Tam Cafe & Bistro",
             address="20/18 Liễu Giai, Cống Vị, Ba Đình, Hà Nội, Việt Nam",
             center_lat=21.032901, center_lng=105.826512, radius_meters=50, status="active"),
        Cafe(name="Cong Caphe Trấn Vũ",
             address="83 Trấn Vũ, Trúc Bạch, Ba Đình, Hà Nội, Việt Nam",
             center_lat=21.044512, center_lng=105.835123, radius_meters=50, status="active"),

        # ===== Đống Đa =====
        Cafe(name="The Wiselands Coffee",
             address="17 Xóm Hà Hồi, Hoàn Kiếm, Hà Nội, Việt Nam",
             center_lat=21.023901, center_lng=105.848523, radius_meters=50, status="active"),
        Cafe(name="Runam Bistro Đống Đa",
             address="7 Huỳnh Thúc Kháng kéo dài, Đống Đa, Hà Nội, Việt Nam",
             center_lat=21.025689, center_lng=105.823412, radius_meters=50, status="active"),
        Cafe(name="Chit Chat Coffee",
             address="39 Ngõ 82 Chùa Láng, Láng Thượng, Đống Đa, Hà Nội, Việt Nam",
             center_lat=21.027841, center_lng=105.817342, radius_meters=50, status="active"),

        # ===== Hai Bà Trưng =====
        Cafe(name="Trill Rooftop Cafe",
             address="338 Phố Huế, Hai Bà Trưng, Hà Nội, Việt Nam",
             center_lat=21.015423, center_lng=105.849823, radius_meters=50, status="active"),
        Cafe(name="6 Degrees Coffee",
             address="114 Bùi Thị Xuân, Hai Bà Trưng, Hà Nội, Việt Nam",
             center_lat=21.022341, center_lng=105.844512, radius_meters=50, status="active"),
        Cafe(name="Cafe Mai Hai Bà Trưng",
             address="96 Lê Văn Hưu, Hai Bà Trưng, Hà Nội, Việt Nam",
             center_lat=21.021234, center_lng=105.849012, radius_meters=50, status="active"),
        Cafe(name="Highlands Coffee Vincom",
             address="191 Bà Triệu, Hai Bà Trưng, Hà Nội, Việt Nam",
             center_lat=21.018423, center_lng=105.849923, radius_meters=50, status="active"),
        Cafe(name="Cong Caphe Triệu Việt Vương",
             address="152 Triệu Việt Vương, Hai Bà Trưng, Hà Nội, Việt Nam",
             center_lat=21.015912, center_lng=105.850234, radius_meters=50, status="active"),

        # ===== Cầu Giấy =====
        Cafe(name="Runam Bistro Cầu Giấy",
             address="47 Trần Thái Tông, Dịch Vọng Hậu, Cầu Giấy, Hà Nội, Việt Nam",
             center_lat=21.031923, center_lng=105.788234, radius_meters=50, status="active"),
        Cafe(name="Runam Bistro Hoàng Ngân",
             address="248 Hoàng Ngân, Cầu Giấy, Hà Nội, Việt Nam",
             center_lat=21.004512, center_lng=105.798234, radius_meters=50, status="active"),
        Cafe(name="Trung Nguyên Legend Cầu Giấy",
             address="241 Xuân Thủy, Dịch Vọng Hậu, Cầu Giấy, Hà Nội, Việt Nam",
             center_lat=21.037812, center_lng=105.782341, radius_meters=50, status="active"),

        # ===== Thanh Xuân =====
        Cafe(name="Runam Bistro Láng Hạ",
             address="50 Láng Hạ, Đống Đa, Hà Nội, Việt Nam",
             center_lat=21.018923, center_lng=105.820312, radius_meters=50, status="active"),
        Cafe(name="Runam Bistro Khương Đình",
             address="268 Khương Đình, Thanh Xuân, Hà Nội, Việt Nam",
             center_lat=20.993123, center_lng=105.812341, radius_meters=50, status="active"),

        # ===== Hà Đông =====
        Cafe(name="Thăng Long Eco Bay Cafe",
             address="Khu sinh thái Thăng Long, Đông Sơn, Chương Mỹ, Hà Nội, Việt Nam",
             center_lat=20.896234, center_lng=105.718512, radius_meters=100, status="active"),

        # ===== Test locations (giữ nguyên) =====
        Cafe(name="Test Location - Your Current GPS",
             address="Hanoi Test Point",
             center_lat=21.5945721, center_lng=105.8420725, radius_meters=50, status="active"),
        Cafe(name="Test Location - Session Exact Match",
             address="Hanoi Session Match Point",
             center_lat=21.5941, center_lng=105.8432, radius_meters=50, status="active"),
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
