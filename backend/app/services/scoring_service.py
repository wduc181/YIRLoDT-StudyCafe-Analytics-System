"""
scoring_service.py — Adapter layer: Backend ↔ Scoring Engine.

INTEGRATED: scoring_engine module đã được tích hợp.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.models.gps_log import GpsLog
from app.models.cafe import Cafe
from app.models.cafe_score import CafeScore

logger = logging.getLogger(__name__)

# Import scoring engine (embedded module)
try:
    from scoring_engine import __version__ as _engine_version
    from scoring_engine import score_session as engine_score_session
    from scoring_engine import update_cafe_score as engine_update_cafe_score
    SCORING_ENGINE_AVAILABLE = True
    logger.info("scoring_engine v%s loaded.", _engine_version)
except ImportError:
    SCORING_ENGINE_AVAILABLE = False
    logger.warning(
        "Không thể import scoring_engine. "
        "Kiểm tra dependencies: numpy, pandas, scikit-learn, scipy, python-dateutil."
    )


def _to_utc_iso(dt: datetime) -> str:
    """
    Chuẩn hoá datetime sang UTC rồi format ISO 8601 với hậu tố "Z".

    - Nếu dt có tzinfo → astimezone(UTC).
    - Nếu dt naive (không có tzinfo) → giả định đã là UTC (DB TIMESTAMPTZ
      trả về aware, nhưng phòng trường hợp ORM strip tz).
    """
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


async def _build_scoring_payload(db: AsyncSession, session_id: str) -> dict | None:
    """
    Build input payload cho scoring engine theo contract api_design.md mục 6.2.

    Returns None nếu session không tồn tại, UUID không hợp lệ, hoặc chưa có cafe_id.
    """
    # 1. Parse UUID — handle invalid format
    try:
        sid = UUID(str(session_id))
    except (ValueError, AttributeError):
        logger.error("Invalid UUID format: %r", session_id)
        return None

    # 2. Lấy session info
    stmt = select(Session).where(Session.session_id == sid)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session or not session.cafe_id:
        return None

    # 3. Lấy cafe info
    cafe_stmt = select(Cafe).where(Cafe.cafe_id == session.cafe_id)
    cafe_result = await db.execute(cafe_stmt)
    cafe = cafe_result.scalar_one_or_none()

    if not cafe:
        return None

    # 4. Lấy GPS logs (sort timestamp tăng dần)
    gps_stmt = (
        select(GpsLog)
        .where(GpsLog.session_id == session.session_id)
        .order_by(GpsLog.timestamp.asc())
    )
    gps_result = await db.execute(gps_stmt)
    gps_logs = gps_result.scalars().all()

    if not gps_logs:
        return None

    # 5. Build cafe_history từ cafe_scores hiện tại
    cafe_history = await _get_cafe_history(db, cafe.cafe_id)

    # 6. Assemble payload theo contract
    # Timestamp serialize theo contract: UTC + hậu tố Z (ISO 8601)
    # Chuẩn hoá sang UTC trước khi format — đảm bảo "Z" suffix đúng nghĩa
    payload = {
        "session_id": str(session.session_id),
        "device_id": session.device_id,
        "cafe": {
            "cafe_id": cafe.cafe_id,
            "center_lat": cafe.center_lat,
            "center_lng": cafe.center_lng,
            "radius_meters": cafe.radius_meters,
        },
        "gps_points": [
            {
                "lat": log.lat,
                "lng": log.lng,
                "accuracy": log.accuracy_m,
                "timestamp": _to_utc_iso(log.timestamp),
            }
            for log in gps_logs
        ],
        "cafe_history": cafe_history,
    }

    return payload


async def _get_cafe_history(db: AsyncSession, cafe_id: int) -> dict:
    """
    Build cafe_history theo contract api_design.md mục 6.2.
    Lấy từ bản ghi cafe_scores mới nhất.
    """
    # Lấy cafe_score mới nhất
    score_stmt = (
        select(CafeScore)
        .where(CafeScore.cafe_id == cafe_id)
        .order_by(CafeScore.computed_at.desc())
        .limit(1)
    )
    score_result = await db.execute(score_stmt)
    latest_score = score_result.scalar_one_or_none()

    # Tính system_avg_score (trung bình behavior_score của tất cả quán có enough data)
    avg_stmt = (
        select(func.avg(CafeScore.behavior_score))
        .where(CafeScore.has_enough_data.is_(True))
    )
    avg_result = await db.execute(avg_stmt)
    system_avg = avg_result.scalar()

    # Default prior 6.5 theo scoring_engine_design.md v0.3 (mục 7.4, 8.2)
    default_prior = 6.5

    if latest_score:
        return {
            "total_sessions_processed": latest_score.total_sessions or 0,
            "current_score": latest_score.behavior_score,
            "studying_session_count": latest_score.studying_sessions or 0,
            "system_avg_score": system_avg or default_prior,
        }

    return {
        "total_sessions_processed": 0,
        "current_score": None,
        "studying_session_count": 0,
        "system_avg_score": system_avg or default_prior,
    }


def _parse_computed_at(cafe_result: dict) -> datetime:
    """
    Parse computed_at từ scoring engine output.
    Ưu tiên giá trị từ engine, fallback datetime.now(UTC).
    Handle cả string ISO 8601 và datetime object, ép UTC nếu naive.
    """
    raw = cafe_result.get("computed_at")
    if not raw:
        return datetime.now(timezone.utc)

    if isinstance(raw, str):
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    elif isinstance(raw, datetime):
        parsed = raw
    else:
        return datetime.now(timezone.utc)

    # Ép UTC nếu naive datetime (không có tzinfo)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


async def _persist_cafe_score(db: AsyncSession, cafe_result: dict) -> None:
    """
    Lưu kết quả cafe scoring vào bảng cafe_scores.
    Mapping từ output contract (api_design.md mục 6.4) → ORM.
    """
    score = CafeScore(
        cafe_id=cafe_result["cafe_id"],
        computed_at=_parse_computed_at(cafe_result),
        total_sessions=cafe_result.get("total_sessions"),
        studying_sessions=cafe_result.get("studying_sessions"),
        study_rate=cafe_result.get("study_rate"),
        avg_stable_duration_min=cafe_result.get("avg_stable_duration_min"),
        avg_spatial_std_m=cafe_result.get("avg_spatial_std_m"),
        dropoff_count=cafe_result.get("dropoff_count"),
        dropoff_rate=cafe_result.get("dropoff_rate"),
        behavior_score=cafe_result.get("behavior_score"),
        has_enough_data=cafe_result.get("has_enough_data", False),
        bayesian_m=cafe_result.get("bayesian_m"),
        prior_score=cafe_result.get("prior_score"),
        engine_version=cafe_result.get("engine_version"),
    )
    db.add(score)
    await db.commit()


async def score_and_update_cafe(db: AsyncSession, session_id: str) -> dict:
    """
    Orchestrator: build payload → gọi scoring engine → persist.

    Gọi trong background task sau khi session kết thúc.
    Nhận DB session riêng (không reuse từ request).

    Returns:
        dict với status và kết quả scoring (hoặc placeholder nếu engine chưa có).
    """
    # 1. Build payload
    payload = await _build_scoring_payload(db, session_id)
    if not payload:
        logger.warning("Không thể build scoring payload cho session %s", session_id)
        return {
            "session_id": session_id,
            "status": "skipped",
            "message": "Session không có cafe_id hoặc không có GPS data",
        }

    # 2. Kiểm tra scoring engine có sẵn không
    if not SCORING_ENGINE_AVAILABLE:
        logger.info(
            "Scoring engine chưa khả dụng (ImportError). Session %s sẽ được xử lý khi "
            "dependencies được cài đặt đầy đủ.",
            session_id,
        )
        return {
            "session_id": session_id,
            "status": "pending",
            "message": (
                "Scoring engine chưa khả dụng do ImportError; "
                "vui lòng kiểm tra dependencies môi trường runtime"
            ),
        }

    # 3. Gọi scoring engine (function call — embedded module)
    try:
        session_result = engine_score_session(payload)
        logger.info(
            "Session %s scored: is_studying=%s",
            session_id,
            session_result.get("is_studying"),
        )

        # 4. Cập nhật cafe score nếu có cafe_history
        # Contract api_design.md §6.2: cafe_history vắng mặt → session-only
        cafe_history = payload.get("cafe_history")
        cafe_result = None

        if cafe_history:
            cafe_result = engine_update_cafe_score(
                cafe_id=payload["cafe"]["cafe_id"],
                session_result=session_result,
                cafe_history=cafe_history,
            )

            # 5. Persist cafe score
            await _persist_cafe_score(db, cafe_result)
            logger.info(
                "Cafe %s score updated: %s",
                cafe_result["cafe_id"],
                cafe_result.get("behavior_score"),
            )
        else:
            logger.info(
                "Session %s: không cập nhật cafe score do thiếu cafe_history.",
                session_id,
            )

        return {
            "session_id": session_id,
            "status": "ok",
            "session_result": session_result,
            "cafe_result": cafe_result,
        }

    except Exception as e:
        logger.exception("Scoring engine error cho session %s", session_id)
        # Rollback để tránh session bị kẹt ở trạng thái "failed transaction"
        await db.rollback()
        return {
            "session_id": session_id,
            "status": "error",
            "message": str(e),
        }
