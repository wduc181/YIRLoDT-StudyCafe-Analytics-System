"""
admin.py — Pydantic Schemas cho Admin/Internal endpoints.
"""

from pydantic import BaseModel


class MockDataImportResponse(BaseModel):
    """Response cho POST /api/mock-data/import."""
    status: str = "ok"
    imported_sessions: int
    imported_logs: int
    scoring_triggered: int
