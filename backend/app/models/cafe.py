# Mapping bảng `cafes` — lưu thông tin quán cafe được mock data.

from sqlalchemy import Column, Integer, String, Float

from app.db.database import Base


class Cafe(Base):
    """Quán cafe mẫu để hệ thống đánh giá."""

    __tablename__ = "cafes"

    cafe_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    address = Column(String, nullable=True)
    center_lat = Column(Float, nullable=False)
    center_lng = Column(Float, nullable=False)
    radius_meters = Column(Integer, default=50)
    status = Column(String(16), default="active")
    # 'active'   : quán mặc định / đã được duyệt
    # 'pending'  : do user đề xuất, chờ admin duyệt
    # 'disabled' : tắt bởi admin
    submitted_by = Column(String(64), nullable=True)  # device_id người đề xuất
    google_place_id = Column(String(255), nullable=True)  # [Optional] Place ID từ Google
