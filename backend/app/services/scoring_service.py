"""
scoring_service.py — Interface gọi Scoring Engine.

QUAN TRỌNG: Không tự implement logic scoring ở đây.
Scoring engine do team riêng phụ trách (xem scoring_engine_design.md).
File này chỉ là interface/adapter layer.

Chờ Scoring team chốt: real-time hay batch? function call hay DB?
Ref: AGENTS.md mục 10, docs/api_design.md mục 6.
"""

from sqlalchemy.ext.asyncio import AsyncSession


async def score_session(db: AsyncSession, session_id: str) -> dict:
    """
    Chuẩn bị input data theo contract (api_design.md mục 6.1),
    gọi scoring engine, nhận output (mục 6.2),
    lưu kết quả vào bảng cafe_scores.

    TODO: Implement khi Scoring team chốt contract.
    Hiện tại trả về placeholder.
    """
    # TODO: Build input theo format api_design.md mục 6.1
    # TODO: Gọi scoring engine (function call / DB / file)
    # TODO: Parse output theo format api_design.md mục 6.2
    # TODO: Lưu kết quả vào cafe_scores
    return {
        "session_id": session_id,
        "status": "pending",
        "message": "Scoring engine chưa được tích hợp, chờ Scoring team chốt",
    }
