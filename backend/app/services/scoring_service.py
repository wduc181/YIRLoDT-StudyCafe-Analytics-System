"""
scoring_service.py — Adapter layer: Backend ↔ Scoring Engine.

TODO: Implement scoring logic

File này chịu trách nhiệm:
1. Build input payload theo contract (api_design.md mục 6.2)
2. Gọi scoring engine qua function call (mục 6.1)
3. Persist kết quả vào DB (cafe_scores)

Khi scoring_engine chưa có → log warning, return placeholder.
Ref: AGENTS.md mục 10, docs/api_design.md mục 6.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.models.gps_log import GpsLog
from app.models.cafe import Cafe
from app.models.cafe_score import CafeScore

logger = logging.getLogger(__name__)

# Import scoring engine (embedded module) — sẽ có khi team scoring deliver
try:
    from scoring_engine import score_session as engine_score_session
    from scoring_engine import update_cafe_score as engine_update_cafe_score
    SCORING_ENGINE_AVAILABLE = True
except ImportError:
    SCORING_ENGINE_AVAILABLE = False
    logger.warning(
        "scoring_engine module chưa có. "
        "Score sẽ không được tính cho đến khi module được cài đặt."
    )


async def _build_scoring_payload(db: AsyncSession, session_id: str) -> dict | None:
    """
    Build input payload cho scoring engine theo contract api_design.md mục 6.2.

    Returns None nếu session không tồn tại hoặc chưa có cafe_id.
    """
    from uuid import UUID

    # 1. Lấy session info
    stmt = select(Session).where(Session.session_id == UUID(session_id))
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session or not session.cafe_id:
        return None

    # 2. Lấy cafe info
    cafe_stmt = select(Cafe).where(Cafe.cafe_id == session.cafe_id)
    cafe_result = await db.execute(cafe_stmt)
    cafe = cafe_result.scalar_one_or_none()

    if not cafe:
        return None

    # 3. Lấy GPS logs (sort timestamp tăng dần)
    gps_stmt = (
        select(GpsLog)
        .where(GpsLog.session_id == session.session_id)
        .order_by(GpsLog.timestamp.asc())
    )
    gps_result = await db.execute(gps_stmt)
    gps_logs = gps_result.scalars().all()

    if not gps_logs:
        return None

    # 4. Build cafe_history từ cafe_scores hiện tại
    cafe_history = await _get_cafe_history(db, cafe.cafe_id)

    # 5. Assemble payload theo contract
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
                "timestamp": log.timestamp.isoformat(),
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

    if latest_score:
        return {
            "total_sessions_processed": latest_score.total_sessions or 0,
            "current_score": latest_score.behavior_score,
            "studying_session_count": latest_score.studying_sessions or 0,
            "system_avg_score": system_avg or 5.0,  # default prior
        }

    return {
        "total_sessions_processed": 0,
        "current_score": None,
        "studying_session_count": 0,
        "system_avg_score": system_avg or 5.0,
    }


async def _persist_cafe_score(db: AsyncSession, cafe_result: dict) -> None:
    """
    Lưu kết quả cafe scoring vào bảng cafe_scores.
    Mapping từ output contract (api_design.md mục 6.4) → ORM.
    """
    score = CafeScore(
        cafe_id=cafe_result["cafe_id"],
        computed_at=datetime.now(timezone.utc),
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

    Gọi sau khi session kết thúc (POST /api/session/end).

    Returns:
        dict với status và kết quả scoring (hoặc placeholder nếu engine chưa có).
    """
    # 1. Build payload
    payload = await _build_scoring_payload(db, session_id)
    if not payload:
        logger.warning(f"Không thể build scoring payload cho session {session_id}")
        return {
            "session_id": session_id,
            "status": "skipped",
            "message": "Session không có cafe_id hoặc không có GPS data",
        }

    # 2. Kiểm tra scoring engine có sẵn không
    if not SCORING_ENGINE_AVAILABLE:
        logger.info(
            f"Scoring engine chưa có. Session {session_id} sẽ được score khi module sẵn sàng."
        )
        return {
            "session_id": session_id,
            "status": "pending",
            "message": "Scoring engine chưa được tích hợp, chờ team scoring deliver module",
        }

    # 3. Gọi scoring engine (function call — embedded module)
    try:
        session_result = engine_score_session(payload)
        logger.info(
            f"Session {session_id} scored: is_studying={session_result.get('is_studying')}"
        )

        # 4. Cập nhật cafe score nếu có cafe_history
        cafe_result = engine_update_cafe_score(
            cafe_id=payload["cafe"]["cafe_id"],
            session_result=session_result,
            cafe_history=payload.get("cafe_history"),
        )

        # 5. Persist cafe score
        await _persist_cafe_score(db, cafe_result)
        logger.info(
            f"Cafe {cafe_result['cafe_id']} score updated: {cafe_result.get('behavior_score')}"
        )

        return {
            "session_id": session_id,
            "status": "ok",
            "session_result": session_result,
            "cafe_result": cafe_result,
        }

    except Exception as e:
        logger.error(f"Scoring engine error cho session {session_id}: {e}")
        return {
            "session_id": session_id,
            "status": "error",
            "message": str(e),
        }
