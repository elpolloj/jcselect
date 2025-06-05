"""Application settings using Pydantic BaseSettings."""
from __future__ import annotations

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

    # Database configuration
    DB_DRIVER: str = Field(
        default="sqlite", description="Database driver: sqlite or mssql"
    )
    DB_USER: str = Field(default="", description="Database username")
    DB_PASS: str = Field(default="", description="Database password")
    DB_HOST: str = Field(default="localhost", description="Database host")
    DB_NAME: str = Field(default="jcselect", description="Database name")
    DB_PORT: int = Field(default=1433, description="Database port")


# ---------------------------------------------------------
# Sync-engine configuration (Sync Spec – Step 2)
# ---------------------------------------------------------
class SyncSettings(BaseSettings):
    """Enhanced sync configuration"""

    model_config = SettingsConfigDict(
        env_file=".env",
        validate_assignment=True
    )

    # Core sync
    sync_api_url: HttpUrl
    sync_jwt_secret: str = Field(min_length=32)
    sync_interval_seconds: int = Field(default=300, ge=60, le=3600)
    sync_max_payload_size: int = Field(default=1_048_576, ge=1_024, le=10_485_760)
    sync_enabled: bool = True

    # Fast sync for TallyLine changes
    sync_fast_tally_enabled: bool = Field(default=True, description="Enable fast sync for tally line changes")

    # Dashboard auto-refresh
    dashboard_poll_secs: int = Field(default=30, ge=5, le=300, description="How often the dashboard counters auto-refresh (seconds)")

    # Pagination
    sync_pull_page_size: int = Field(default=100, ge=10, le=1_000)
    sync_max_pull_pages: int = Field(default=10, ge=1, le=100)

    # Retry / back-off
    sync_max_retries: int = Field(default=5, ge=1, le=10)
    sync_backoff_base: float = Field(default=2.0, ge=1.0, le=5.0)
    sync_backoff_max_seconds: int = Field(default=300, ge=60, le=1_800)

    # JWT Authentication
    jwt_access_token_expire_minutes: int = Field(default=15, ge=1, le=60)
    jwt_refresh_token_expire_hours: int = Field(default=12, ge=1, le=24)
    jwt_algorithm: str = Field(default="HS256")

    # CORS Configuration
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = Field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    cors_allow_headers: list[str] = Field(default_factory=lambda: ["*"])

    # Dependency ordering (parents → children)
    sync_entity_order: list[str] = Field(
        default_factory=lambda: [
            "User", "Party", "Pen",
            "TallySession",
            "Voter", "TallyLine",
            "AuditLog",
        ]
    )


def _create_sync_settings() -> SyncSettings:
    """Create sync settings instance from environment variables."""
    # mypy doesn't understand that pydantic-settings gets values from env vars
    try:
        return SyncSettings()  # type: ignore[call-arg]
    except Exception:
        # For testing/development, provide minimal defaults
        import os
        os.environ.setdefault("SYNC_API_URL", "http://localhost:8000")
        os.environ.setdefault("SYNC_JWT_SECRET", "test-secret-key-for-development-only-32-chars-long")
        return SyncSettings()  # type: ignore[call-arg]


# Global settings instances
settings = Settings()
sync_settings = _create_sync_settings()
