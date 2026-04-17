"""
main.py — FastAPI Application Entrypoint.

Khởi tạo FastAPI app, CORS middleware, include routers, lifespan events.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import init_db, close_db

# Logging config — format chuẩn cho toàn backend
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("studycafe")

# Import models để Base.metadata nhận đủ tables
import app.models  # noqa: F401

from app.routers import cafes, sessions, tracking, report, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
        logger.info("Database connected and tables created.")
    except Exception as e:
        logger.error("Database connection failed: %s", e)
        logger.warning("App sẽ vẫn chạy nhưng các API cần DB sẽ lỗi.")
        logger.warning("Hãy kiểm tra DATABASE_URL trong .env và đảm bảo PostgreSQL đang chạy.")
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
