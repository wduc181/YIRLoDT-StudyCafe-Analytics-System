"""
config.py — Application Configuration.

TODO:
- Dùng pydantic-settings BaseSettings để đọc từ .env.
- Khai báo các biến config:
  - DATABASE_URL: str
  - CORS_ORIGINS: str (parse thành list)
  - GPS_TRACKING_INTERVAL_SECONDS: int = 60
  - CAFE_RADIUS_DEFAULT_METERS: int = 50
  - NEARBY_CAFES_DEFAULT_LIMIT: int = 5
  - GOOGLE_PLACES_API_KEY: str = "" (optional)
- Tạo singleton `settings = Settings()`.
- Ref: AGENTS.md mục 5, app/core/config.py.
"""
