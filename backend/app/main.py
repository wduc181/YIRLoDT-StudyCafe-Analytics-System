"""
main.py — FastAPI Application Entrypoint.

Khởi tạo FastAPI app, CORS middleware, include routers, lifespan events.
Ref: docs/api_design.md mục 2 (nguyên tắc thiết kế API).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import init_db, close_db

# Import models để Base.metadata nhận đủ tables
import app.models  # noqa: F401

from app.routers import cafes, sessions, tracking, report, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event: init DB on startup, close on shutdown."""
    try:
        await init_db()
        print("✅ Database connected and tables created.")
    except Exception as e:
        print(f"⚠️  Database connection failed: {e}")
        print("   App sẽ vẫn chạy nhưng các API cần DB sẽ lỗi.")
        print("   Hãy kiểm tra DATABASE_URL trong .env và đảm bảo PostgreSQL đang chạy.")
    yield
    try:
        await close_db()
    except Exception:
        pass


app = FastAPI(
    title="StudyCafe Analytics System",
    description="Hệ thống đánh giá địa điểm học tập qua hành vi GPS",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware — đọc origins từ config, không hardcode
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers với prefix /api/
app.include_router(cafes.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(tracking.router, prefix="/api")
app.include_router(report.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "app": "StudyCafe Analytics System"}
