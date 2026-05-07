"""
config.py — Application Configuration.

Dùng pydantic-settings BaseSettings để đọc từ .env.
Ref: AGENTS.md mục 5, app/core/config.py.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings — đọc từ .env file."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/studycafe"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173"

    # GPS Tracking
    GPS_TRACKING_INTERVAL_SECONDS: int = 60

    # Cafe
    CAFE_RADIUS_DEFAULT_METERS: int = 50
    NEARBY_CAFES_DEFAULT_LIMIT: int = 20

    # Google Places (optional)
    GOOGLE_PLACES_API_KEY: str = ""

    # Internal endpoints
    REPORT_EXPORT_TOKEN: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS thành list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = {
        "env_file": os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".env"
        ),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Singleton instance
settings = Settings()
