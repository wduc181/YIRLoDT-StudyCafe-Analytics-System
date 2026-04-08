"""
database.py — Database Connection và Engine Setup.

TODO:
- Tạo async engine từ DATABASE_URL (config.py).
- Tạo async_sessionmaker.
- Tạo Base = declarative_base() cho ORM models.
- Hàm init_db() để tạo tables (dev only).
- Ref: AGENTS.md mục 3, dùng SQLAlchemy async session + asyncpg.
"""
