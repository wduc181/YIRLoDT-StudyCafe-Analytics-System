"""
scoring_engine — Module đánh giá hành vi học tập từ dữ liệu GPS.

Public API (backend import trực tiếp):
    score_session(payload)           → dict (session-level result)
    update_cafe_score(...)           → dict (cafe-level result)

Ví dụ sử dụng (trong backend/app/services/scoring_service.py):
    from scoring_engine import score_session, update_cafe_score

    session_result = score_session(payload)
    cafe_result    = update_cafe_score(
        cafe_id        = payload["cafe"]["cafe_id"],
        session_result = session_result,
        cafe_history   = payload.get("cafe_history"),
    )
    # Backend tự persist session_result và cafe_result vào DB
"""

from scoring_engine import config as _engine_config
from scoring_engine.pipeline import score_session, run_update_cafe_score as update_cafe_score

__all__ = ["score_session", "update_cafe_score"]
__version__ = _engine_config.ENGINE_VERSION
