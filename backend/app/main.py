"""
main.py — FastAPI Application Entrypoint.

TODO:
- Khởi tạo FastAPI app instance.
- Cấu hình CORS middleware (đọc CORS_ORIGINS từ config).
- Include tất cả routers với prefix /api/.
- Setup lifespan event để init/close DB connection pool.
- Ref: docs/api_design.md mục 2 (nguyên tắc thiết kế API).
"""
