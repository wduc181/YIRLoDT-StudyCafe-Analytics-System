"""
main.py — FastAPI Application Entrypoint.

Khởi tạo FastAPI app, CORS middleware, include routers, lifespan events.
"""

import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.db.database import init_db, close_db

# Logging config — dùng dictConfig để không bị uvicorn override
# disable_existing_loggers=False giữ uvicorn loggers hoạt động bình thường
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "studycafe": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "app": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}
logging.config.dictConfig(LOGGING_CONFIG)
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


def _validation_error_message(request: Request, exc: RequestValidationError) -> str:
    """Map FastAPI validation details to the project error contract."""
    errors = exc.errors()

    for error in errors:
        loc = tuple(error.get("loc", ()))
        if (
            request.url.path == "/api/session/start"
            and loc in (("body",), ("body", "device_id"))
            and error.get("type") == "missing"
        ):
            return "device_id is required"

    for error in errors:
        loc = tuple(error.get("loc", ()))
        if "lat" in loc or "lng" in loc:
            return "invalid coordinates"
        if "session_id" in loc:
            return "invalid session_id"

    if errors:
        message = errors[0].get("msg")
        if isinstance(message, str):
            return message
    return "invalid request"


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    """Preserve status code while returning top-level status/message errors."""
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message") or detail.get("detail") or str(detail)
    elif isinstance(detail, str):
        message = detail
    else:
        message = str(detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": message},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    message = _validation_error_message(request, exc)
    status_code = 400 if message == "device_id is required" else 422
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "message": message,
        },
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
